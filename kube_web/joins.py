import collections
import logging
from typing import Dict

import pykube
from pykube.objects import NamespacedAPIObject

from kube_web import kubernetes
from kube_web import query_params as qp

logger = logging.getLogger(__name__)


async def join_metrics(
    wrap_query, _cluster, table, namespace: str, is_all_namespaces: bool, params: dict,
):
    if not table.rows:
        # nothing to do
        return

    table.columns.append({"name": "CPU Usage"})
    table.columns.append({"name": "Memory Usage"})

    if table.api_obj_class.kind == "Pod":
        clazz = kubernetes.PodMetrics
    elif table.api_obj_class.kind == "Node":
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
