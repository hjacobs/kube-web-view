import collections
import logging
import re
from typing import Dict

import jmespath
import pykube
from pykube.objects import NamespacedAPIObject
from pykube.objects import Node
from pykube.objects import Pod

from kube_web import kubernetes
from kube_web import query_params as qp

logger = logging.getLogger(__name__)

NON_WORD_CHARS = re.compile("[^0-9a-zA-Z]+")
SECRET_CONTENT_HIDDEN = "**SECRET-CONTENT-HIDDEN-BY-KUBE-WEB-VIEW**"


def generate_name_from_spec(spec: str) -> str:
    words = NON_WORD_CHARS.split(spec)
    name = " ".join([word.capitalize() for word in words if word])
    return name


async def join_metrics(
    wrap_query, _cluster, table, namespace: str, is_all_namespaces: bool, params: dict,
):
    if not table.rows:
        # nothing to do
        return

    table.columns.append({"name": "CPU Usage"})
    table.columns.append({"name": "Memory Usage"})

    if table.api_obj_class.kind == Pod.kind:
        clazz = kubernetes.PodMetrics
    elif table.api_obj_class.kind == Node.kind:
        clazz = kubernetes.NodeMetrics

    row_index_by_namespace_name = {}
    for i, row in enumerate(table.rows):
        row_index_by_namespace_name[
            (
                row["object"]["metadata"].get("namespace"),
                row["object"]["metadata"]["name"],
            )
        ] = i

    query = wrap_query(clazz.objects(_cluster.api))

    if issubclass(clazz, NamespacedAPIObject):
        if is_all_namespaces:
            query = query.filter(namespace=pykube.all)
        elif namespace:
            query = query.filter(namespace=namespace)

    if params.get(qp.SELECTOR):
        query = query.filter(selector=params[qp.SELECTOR])

    rows_joined = set()

    try:
        metrics_list = await kubernetes.get_list(query)
    except Exception as e:
        logger.warning(f"Failed to query {clazz.kind} in cluster {_cluster.name}: {e}")
    else:
        for metrics in metrics_list:
            key = (metrics.namespace, metrics.name)
            row_index = row_index_by_namespace_name.get(key)
            if row_index is not None:
                usage: Dict[str, float] = collections.defaultdict(float)
                if "containers" in metrics.obj:
                    for container in metrics.obj["containers"]:
                        for k, v in container.get("usage", {}).items():
                            usage[k] += kubernetes.parse_resource(v)
                else:
                    for k, v in metrics.obj.get("usage", {}).items():
                        usage[k] += kubernetes.parse_resource(v)

                table.rows[row_index]["cells"].extend(
                    [usage.get("cpu", 0), usage.get("memory", 0)]
                )
                rows_joined.add(row_index)

    # fill up cells where we have no metrics
    for i, row in enumerate(table.rows):
        if i not in rows_joined:
            # use zero instead of None to allow sorting
            row["cells"].extend([0, 0])


async def join_custom_columns(
    wrap_query,
    _cluster,
    table,
    namespace: str,
    is_all_namespaces: bool,
    custom_columns_param: str,
    params: dict,
    config,
):
    if not table.rows:
        # nothing to do
        return

    clazz = table.api_obj_class

    custom_column_names = []
    custom_columns = {}
    for part in filter(None, custom_columns_param.split(";")):
        name, _, spec = part.partition("=")
        if not spec:
            spec = name
            name = generate_name_from_spec(spec)
        custom_column_names.append(name)
        custom_columns[name] = jmespath.compile(spec)

    if not custom_columns:
        # nothing to do
        return

    for name in custom_column_names:
        table.columns.append({"name": name})

    row_index_by_namespace_name = {}
    for i, row in enumerate(table.rows):
        row_index_by_namespace_name[
            (
                row["object"]["metadata"].get("namespace"),
                row["object"]["metadata"]["name"],
            )
        ] = i

    nodes = None
    if params.get(qp.JOIN) == "nodes" and clazz.kind == Pod.kind:
        node_query = wrap_query(Node.objects(_cluster.api))
        try:
            node_list = await kubernetes.get_list(node_query)
        except Exception as e:
            logger.warning(
                f"Failed to query {Node.kind} in cluster {_cluster.name}: {e}"
            )
        else:
            nodes = {}
            for node in node_list:
                nodes[node.name] = node

    query = wrap_query(clazz.objects(_cluster.api))

    if issubclass(clazz, NamespacedAPIObject):
        if is_all_namespaces:
            query = query.filter(namespace=pykube.all)
        elif namespace:
            query = query.filter(namespace=namespace)

    if params.get(qp.SELECTOR):
        query = query.filter(selector=params[qp.SELECTOR])

    rows_joined = set()

    try:
        object_list = await kubernetes.get_list(query)
    except Exception as e:
        logger.warning(f"Failed to query {clazz.kind} in cluster {_cluster.name}: {e}")
    else:
        for obj in object_list:
            key = (obj.namespace, obj.name)
            row_index = row_index_by_namespace_name.get(key)
            if row_index is not None:
                for name in custom_column_names:
                    expression = custom_columns[name]
                    if clazz.kind == "Secret" and not config.show_secrets:
                        value = SECRET_CONTENT_HIDDEN
                    else:
                        if nodes:
                            node = nodes.get(obj.obj["spec"].get("nodeName"))
                            data = {"node": node and node.obj}
                            data.update(obj.obj)
                        else:
                            data = obj.obj
                        value = expression.search(data)
                    table.rows[row_index]["cells"].append(value)
                rows_joined.add(row_index)

    # fill up cells where we have no values
    for i, row in enumerate(table.rows):
        if i not in rows_joined:
            row["cells"].extend([None] * len(custom_column_names))
