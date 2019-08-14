import asyncio
import aiohttp_jinja2
import collections
import jinja2
import csv
import zlib
import colorsys
import json
import base64
import time
import os
import pykube
import logging
import requests.exceptions
import pykube.exceptions
from yarl import URL
from http import HTTPStatus
import yaml

from functools import partial

from pykube import ObjectDoesNotExist, HTTPClient
from pykube.objects import NamespacedAPIObject, Namespace, Event, Pod
from pykube.query import Query
from aiohttp_session import get_session, setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_remotes import XForwardedRelaxed
from aioauth_client import OAuth2Client
from cryptography.fernet import Fernet

from .cluster_manager import ClusterNotFound
from .resource_registry import ResourceTypeNotFound
from .selector import parse_selector, selector_matches

from pathlib import Path

from aiohttp import web

from kube_web import __version__
from kube_web import kubernetes
from kube_web import jinja2_filters
from .table import add_label_columns, filter_table, sort_table, merge_cluster_tables

# import tracemalloc
# tracemalloc.start()

logger = logging.getLogger(__name__)

HEALTH_PATH = "/health"
OAUTH2_CALLBACK_PATH = "/oauth2/callback"

CLUSTER_MANAGER = "cluster_manager"
CONFIG = "config"

ALL = "_all"

ONE_WEEK = 7 * 24 * 60 * 60
FIVE_MINUTES = 5 * 60

SEARCH_DEFAULT_RESOURCE_TYPES = [
    "namespaces",
    "deployments",
    "services",
    "ingresses",
    "statefulsets",
    "cronjobs",
]

SEARCH_OFFERED_RESOURCE_TYPES = [
    "namespaces",
    "deployments",
    "replicasets",
    "services",
    "ingresses",
    "daemonsets",
    "statefulsets",
    "cronjobs",
    "pods",
    "nodes",
]

SEARCH_MATCH_CONTEXT_LENGTH = 20


TABLE_CELL_FORMATTING = {
    "events": {"Type": {"Warning": "has-text-warning"}},
    "persistentvolumeclaims": {
        "Status": {"Pending": "has-text-warning", "Bound": "has-text-success"}
    },
    "persistentvolumes": {
        "Status": {"Terminating": "has-text-danger", "Bound": "has-text-success"}
    },
    "nodes": {"Status": {"Ready": "has-text-success"}},
    "namespaces": {"Status": {"Active": "has-text-success"}},
    "deployments": {"Available": {"0": "has-text-danger"}},
    "pods": {
        "CPU Usage": {"0": "has-text-grey"},
        "Memory Usage": {"0": "has-text-grey"},
        "Status": {
            "Completed": "has-text-info",
            "ContainerCreating": "has-text-warning",
            "CrashLoopBackOff": "has-text-danger",
            "CreateContainerConfigError": "has-text-danger",
            "ErrImagePull": "has-text-danger",
            "Error": "has-text-danger",
            "Evicted": "has-text-danger",
            "ImagePullBackOff": "has-text-danger",
            "OOMKilled": "has-text-danger",
            "OutOfcpu": "has-text-danger",
            "Pending": "has-text-warning",
            "Running": "has-text-success",
            "Terminating": "has-text-warning",
        },
    },
}


routes = web.RouteTableDef()


class HTTPClientWithAccessToken(HTTPClient):
    def __init__(self, base, access_token):
        self.__dict__ = base.__dict__
        self._access_token = access_token
        self.config.user["token"] = None

    def get(self, *args, **kwargs):
        kwargs["auth"] = None
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"]["Authorization"] = f"Bearer {self._access_token}"
        return super().get(*args, **kwargs)


def wrap_query(query: Query, request, session):
    """Wrap a pykube Query object to inject the OAuth2 session token (if configured)"""
    if request.app[CONFIG].cluster_auth_use_session_token:
        query.api = HTTPClientWithAccessToken(query.api, session["access_token"])
    return query


def get_clusters(request, cluster: str):
    is_all_clusters = not bool(cluster) or cluster == ALL
    if is_all_clusters:
        clusters = request.app[CLUSTER_MANAGER].clusters
    else:
        parts = cluster.split(",")
        clusters = list(
            [request.app[CLUSTER_MANAGER].get(_cluster) for _cluster in parts]
        )
    return clusters, is_all_clusters


def context():
    def decorator(func):
        async def func_wrapper(request):
            session = await get_session(request)
            ctx = await func(request, session)
            if isinstance(ctx, dict) and ctx.get("cluster"):
                clusters, is_all_clusters = get_clusters(request, ctx["cluster"])
                if not is_all_clusters and len(clusters) == 1:
                    cluster = clusters[0]
                    namespaces = await kubernetes.get_list(
                        wrap_query(Namespace.objects(cluster.api), request, session)
                    )
                    ctx["namespaces"] = namespaces
            ctx["rel_url"] = request.rel_url
            return ctx

        return func_wrapper

    return decorator


@routes.get("/")
async def get_index(request):
    # we don't have anything to present on the homepage, so let's redirect to the cluster list
    # or the cluster detail page (if we only have one cluster)
    clusters = request.app[CLUSTER_MANAGER].clusters
    if len(clusters) == 1:
        target = f"/clusters/{clusters[0].name}"
    else:
        target = "/clusters"
    raise web.HTTPFound(location=target)


def filter_matches(_filter_lower, cluster):
    if not _filter_lower:
        return True
    return _filter_lower in cluster.name.lower() or _filter_lower in " ".join(
        cluster.labels.values()
    )


@routes.get("/clusters")
@aiohttp_jinja2.template("clusters.html")
@context()
async def get_cluster_list(request, session):
    selector = parse_selector(request.query.get("selector"))
    _filter_lower = request.query.get("filter", "").lower()
    clusters = []
    for cluster in request.app[CLUSTER_MANAGER].clusters:
        if selector_matches(selector, cluster.labels) and filter_matches(
            _filter_lower, cluster
        ):
            clusters.append(cluster)
    clusters.sort(key=lambda c: c.name)
    return {"clusters": clusters}


@routes.get("/clusters/{cluster}")
@aiohttp_jinja2.template("cluster.html")
@context()
async def get_cluster(request, session):
    cluster = request.app[CLUSTER_MANAGER].get(request.match_info["cluster"])
    namespaces = await kubernetes.get_list(
        wrap_query(Namespace.objects(cluster.api), request, session)
    )
    resource_types = await cluster.resource_registry.cluster_resource_types
    return {
        "cluster": cluster.name,
        "cluster_obj": cluster,
        "namespace": None,
        "namespaces": namespaces,
        "resource_types": sorted(resource_types, key=lambda t: (t.kind, t.version)),
    }


def get_cell_class(table, column_index, value):
    cell_formatting = TABLE_CELL_FORMATTING.get(table.api_obj_class.endpoint)
    if not cell_formatting:
        return ""
    cell_formatting = cell_formatting.get(table.columns[column_index]["name"])
    if not cell_formatting:
        return ""
    return cell_formatting.get(str(value))


@routes.get("/clusters/{cluster}/_resource-types")
@aiohttp_jinja2.template("resource-types.html")
@context()
async def get_cluster_resource_types(request, session):
    cluster = request.match_info["cluster"]
    clusters, is_all_clusters = get_clusters(request, cluster)
    resource_types = set()
    for _cluster in clusters:
        for clazz in await _cluster.resource_registry.cluster_resource_types:
            resource_types.add(clazz)
    return {
        "cluster": cluster,
        "is_all_clusters": is_all_clusters,
        "namespace": None,
        "resource_types": sorted(resource_types, key=lambda t: (t.kind, t.version)),
    }


async def join_metrics(
    request,
    session,
    _cluster,
    table,
    namespace: str,
    is_all_namespaces: bool,
    params: dict,
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

    query = wrap_query(clazz.objects(_cluster.api), request, session)

    if issubclass(clazz, NamespacedAPIObject):
        if is_all_namespaces:
            query = query.filter(namespace=pykube.all)
        elif namespace:
            query = query.filter(namespace=namespace)

    if params.get("selector"):
        query = query.filter(selector=params["selector"])

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
                usage = collections.defaultdict(float)
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


async def do_get_resource_list(
    request,
    session,
    _type: str,
    _cluster,
    namespace: str,
    is_all_namespaces: bool,
    params: dict,
):
    """Query cluster resources and return a Table object or error"""
    clazz = table = error = None
    try:
        clazz = await _cluster.resource_registry.get_class_by_plural_name(
            _type, namespaced=namespace is not None
        )
        query = wrap_query(clazz.objects(_cluster.api), request, session)
        if is_all_namespaces:
            query = query.filter(namespace=pykube.all)
        elif namespace:
            query = query.filter(namespace=namespace)

        if params.get("selector"):
            query = query.filter(selector=params["selector"])

        table = await kubernetes.get_table(query)
    except Exception as e:
        # just log as DEBUG because the error is shown in the web frontend already
        logger.debug(f"Failed to list {_type} in {_cluster.name}: {e}")
        error = {"cluster": _cluster, "resource_type": _type, "exception": e}
    else:
        # table.rows might be None, e.g. for "csinodes"
        if table.rows is None:
            table.obj["rows"] = []
        label_columns = params.get("labelcols") or request.app[
            CONFIG
        ].default_label_columns.get(_type)
        add_label_columns(table, label_columns)
        filter_table(table, params.get("filter"))

        # note: we join before sorting, so sorting works on the joined columns, too
        if params.get("join") == "metrics" and _type in ("pods", "nodes"):
            await join_metrics(
                request, session, _cluster, table, namespace, is_all_namespaces, params
            )

        sort_table(table, params.get("sort"))
        for row in table.rows:
            row["cluster"] = _cluster
        table.obj["clusters"] = [_cluster]
    return clazz, table, error


class ResponseWriter:
    def __init__(self, response):
        self.response = response
        self.data = ""

    def write(self, data):
        self.data += data

    async def flush(self):
        await self.response.write(self.data.encode("utf-8"))
        self.data = ""


async def as_tsv(table, fd) -> str:
    writer = csv.writer(fd, delimiter="\t", lineterminator="\n")
    is_multi_cluster = len(table.obj["clusters"]) > 1
    columns = []
    if is_multi_cluster:
        columns.append("Cluster")
    if issubclass(table.api_obj_class, NamespacedAPIObject):
        columns.append("Namespace")
    columns.extend(col["name"] for col in table.columns)
    writer.writerow(columns)
    for row in table.rows:
        additional_cells = []
        cells = row["cells"]
        if is_multi_cluster:
            additional_cells.append(row["cluster"].name)
        if issubclass(table.api_obj_class, NamespacedAPIObject):
            additional_cells.append(row["object"]["metadata"]["namespace"])
        writer.writerow(additional_cells + cells)
        await fd.flush()


async def download_tsv(request, table):
    response = web.StreamResponse()
    response.content_type = "text/tab-separated-values; charset=utf-8"
    path = request.rel_url.path
    filename = path.strip("/").replace("/", "_")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}.tsv"'
    await response.prepare(request)
    await as_tsv(table, ResponseWriter(response))
    return response


async def download_yaml(request, resource):
    response = web.StreamResponse()
    response.content_type = "text/vnd.yaml; charset=utf-8"
    path = request.rel_url.path
    filename = path.strip("/").replace("/", "_")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}.yaml"'
    await response.prepare(request)
    data = yaml.dump(resource.obj, default_flow_style=False)
    await response.write(data.encode("utf-8"))
    return response


@routes.get("/clusters/{cluster}/namespaces/{namespace}/_resource-types")
@aiohttp_jinja2.template("resource-types.html")
@context()
async def get_namespaced_resource_types(request, session):
    cluster = request.match_info["cluster"]
    clusters, is_all_clusters = get_clusters(request, cluster)
    namespace = request.match_info["namespace"]
    resource_types = set()
    for _cluster in clusters:
        for clazz in await _cluster.resource_registry.namespaced_resource_types:
            resource_types.add(clazz)
    return {
        "cluster": cluster,
        "is_all_clusters": is_all_clusters,
        "namespace": namespace,
        "resource_types": sorted(resource_types, key=lambda t: (t.kind, t.version)),
    }


@routes.get("/clusters/{cluster}/{plural}")
@routes.get("/clusters/{cluster}/namespaces/{namespace}/{plural}")
@aiohttp_jinja2.template("resource-list.html")
@context()
async def get_resource_list(request, session):
    cluster = request.match_info["cluster"]
    clusters, is_all_clusters = get_clusters(request, cluster)
    namespace = request.match_info.get("namespace")
    plural = request.match_info["plural"]

    is_all_namespaces = namespace == ALL

    # "all" resource types only work for namespaced types
    if plural == "all" and namespace:
        # this list was extracted from kubectl get all --v=9
        resource_types = [
            "pods",
            "services",
            "daemonsets",
            "deployments",
            "replicasets",
            "statefulsets",
            "horizontalpodautoscalers",
            "jobs",
            "cronjobs",
        ]
    else:
        resource_types = plural.split(",")

    start = time.time()
    params = request.rel_url.query
    tasks = []
    for _type in resource_types:
        for _cluster in clusters:
            task = asyncio.create_task(
                do_get_resource_list(
                    request,
                    session,
                    _type,
                    _cluster,
                    namespace,
                    is_all_namespaces,
                    params,
                )
            )
            tasks.append(task)

    tables = []
    tables_by_resource_type = {}
    errors_by_cluster = collections.defaultdict(list)
    for clazz, table, error in await asyncio.gather(*tasks):
        if error:
            if len(clusters) == 1:
                # directly re-raise the exception as single cluster was given
                raise error["exception"]
            errors_by_cluster[error["cluster"].name].append(error)
        else:
            previous_table = tables_by_resource_type.get(table.api_obj_class.endpoint)
            if previous_table:
                merged = merge_cluster_tables(previous_table, table)
                if merged:
                    # sort again after merge
                    sort_table(merged, params.get("sort"))
                else:
                    tables.append(table)
            else:
                tables_by_resource_type[table.api_obj_class.endpoint] = table
                tables.append(table)

    total_rows = sum(len(table.rows) for table in tables)

    duration = time.time() - start

    if params.get("download") == "tsv":
        return await download_tsv(request, tables[0])

    return {
        "cluster": cluster,
        "is_all_clusters": is_all_clusters,
        "namespace": namespace,
        "is_all_namespaces": is_all_namespaces,
        "plural": plural,
        "tables": tables,
        "get_cell_class": get_cell_class,
        "list_errors": errors_by_cluster,
        "list_duration": duration,
        "list_resource_types": resource_types,
        "list_clusters": clusters,
        "list_total_rows": total_rows,
    }


@routes.get("/clusters/{cluster}/{plural}/{name}")
@routes.get("/clusters/{cluster}/namespaces/{namespace}/{plural}/{name}")
@aiohttp_jinja2.template("resource-view.html")
@context()
async def get_resource_view(request, session):
    cluster = request.app[CLUSTER_MANAGER].get(request.match_info["cluster"])
    namespace = request.match_info.get("namespace")
    plural = request.match_info["plural"]
    name = request.match_info["name"]
    params = request.rel_url.query
    view = params.get("view")
    clazz = await cluster.resource_registry.get_class_by_plural_name(
        plural, namespaced=bool(namespace)
    )
    query = wrap_query(clazz.objects(cluster.api), request, session)
    if namespace:
        query = query.filter(namespace=namespace)
    resource = await kubernetes.get_by_name(query, name)

    if resource.kind == "Secret" and not request.app[CONFIG].show_secrets:
        # mask out all secret values, but still show keys
        for key in resource.obj.get("data", {}).keys():
            resource.obj["data"][key] = "**SECRET-CONTENT-HIDDEN-BY-KUBE-WEB-VIEW**"
        # the secret data is also leaked in annotations ("last-applied-configuration")
        # => hide annotations
        resource.metadata["annotations"] = {"annotations-hidden": "by-kube-web-view"}

    if params.get("download") == "yaml":
        return await download_yaml(request, resource)

    owners = []
    for ref in resource.metadata.get("ownerReferences", []):
        owner_class = await cluster.resource_registry.get_class_by_api_version_kind(
            ref["apiVersion"], ref["kind"], namespaced=bool(namespace)
        )
        owners.append({"name": ref["name"], "class": owner_class})

    selector = field_selector = None
    if resource.kind == "Node":
        field_selector = {"spec.nodeName": resource.name}
    elif resource.obj.get("spec", {}).get("selector", {}).get("matchLabels"):
        # e.g. Deployment, DaemonSet, ..
        selector = resource.obj["spec"]["selector"]["matchLabels"]
    elif resource.obj.get("spec", {}).get("selector"):
        # e.g. Service
        selector = resource.obj["spec"]["selector"]

    if selector or field_selector:
        query = wrap_query(Pod.objects(cluster.api), request, session).filter(
            namespace=namespace or pykube.all
        )

        if selector:
            query = query.filter(selector=selector)
        if field_selector:
            query = query.filter(field_selector=field_selector)

        table = await kubernetes.get_table(query)
        sort_table(table, params.get("sort"))
        table.obj["cluster"] = cluster
    else:
        table = None

    field_selector = {
        "involvedObject.name": resource.name,
        "involvedObject.namespace": namespace or "",
        "involvedObject.kind": resource.kind,
        "involvedObject.uid": resource.metadata["uid"],
    }
    events = await kubernetes.get_list(
        wrap_query(Event.objects(cluster.api), request, session).filter(
            namespace=namespace or pykube.all, field_selector=field_selector
        )
    )

    if resource.kind == "Namespace":
        namespace = resource.name

    return {
        "cluster": cluster.name,
        "namespace": namespace,
        "plural": plural,
        "resource": resource,
        "owners": owners,
        "view": view,
        "table": table,
        "events": events,
        "get_cell_class": get_cell_class,
    }


def pod_color(name):
    """Return HTML color calculated from given pod name.
    """

    if name is None:
        return "#ffa000"
    v = zlib.crc32(name.encode("utf-8"))
    r, g, b = colorsys.hsv_to_rgb((v % 300 + 300) / 1000.0, 0.7, 0.7)
    # g = (v % 7) * 20 + 115;
    # b = (v % 10) * 20 + 55;
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


@routes.get("/clusters/{cluster}/namespaces/{namespace}/{plural}/{name}/logs")
@aiohttp_jinja2.template("resource-logs.html")
@context()
async def get_resource_logs(request, session):
    cluster = request.app[CLUSTER_MANAGER].get(request.match_info["cluster"])
    namespace = request.match_info.get("namespace")
    plural = request.match_info["plural"]
    name = request.match_info["name"]
    tail_lines = int(request.rel_url.query.get("tail_lines") or 200)
    clazz = await cluster.resource_registry.get_class_by_plural_name(
        plural, namespaced=True
    )
    query = wrap_query(clazz.objects(cluster.api), request, session)
    if namespace:
        query = query.filter(namespace=namespace)
    resource = await kubernetes.get_by_name(query, name)

    if resource.kind == "Pod":
        pods = [resource]
    elif resource.obj.get("spec", {}).get("selector", {}).get("matchLabels"):
        query = wrap_query(Pod.objects(cluster.api), request, session).filter(
            namespace=namespace,
            selector=resource.obj["spec"]["selector"]["matchLabels"],
        )
        pods = await kubernetes.get_list(query)
    else:
        raise web.HTTPNotFound(text="Resource has no logs")

    logs = []

    show_container_logs = request.app[CONFIG].show_container_logs
    if show_container_logs:
        for pod in pods:
            color = pod_color(pod.name)
            for container in pod.obj["spec"]["containers"]:
                container_log = await kubernetes.logs(
                    pod,
                    container=container["name"],
                    timestamps=True,
                    tail_lines=tail_lines,
                )
                for line in container_log.split("\n"):
                    # this is a hacky way to determine whether it's a multi-line log message
                    # (our current year of the timestamp starts with "20"..)
                    if line.startswith("20") or not logs:
                        logs.append((line, pod.name, color, container["name"]))
                    else:
                        logs[-1] = (
                            logs[-1][0] + "\n" + line,
                            pod.name,
                            color,
                            container["name"],
                        )

    logs.sort()

    return {
        "cluster": cluster.name,
        "namespace": namespace,
        "plural": plural,
        "resource": resource,
        "tail_lines": tail_lines,
        "pods": pods,
        "logs": logs,
        "show_container_logs": show_container_logs,
    }


async def search(
    request,
    session,
    selector,
    filter_query,
    _type,
    _cluster,
    namespace,
    is_all_namespaces,
):
    clazz = None
    results = []
    errors = []
    try:
        namespaced = True
        clazz = await _cluster.resource_registry.get_class_by_plural_name(
            _type, namespaced=True, default=None
        )
        if not clazz:
            clazz = await _cluster.resource_registry.get_class_by_plural_name(
                _type, namespaced=False
            )
            namespaced = False

        # without a search query, only return the clazz
        if selector or filter_query:
            query = wrap_query(clazz.objects(_cluster.api), request, session)
            if namespaced:
                query = query.filter(
                    namespace=pykube.all if is_all_namespaces else namespace
                )
            if selector:
                query = query.filter(selector=selector)

            table = await kubernetes.get_table(query)
            if filter_query:
                add_label_columns(table, "*")
                filter_table(table, filter_query)
            name_column = 0
            for i, col in enumerate(table.columns):
                if col["name"] == "Name":
                    name_column = i
                    break
            filter_query_lower = filter_query.lower()
            for row in table.rows:
                name = row["cells"][name_column]
                if namespaced:
                    ns = row["object"]["metadata"]["namespace"]
                    link = f"/clusters/{_cluster.name}/namespaces/{ns}/{_type}/{name}"
                else:
                    link = f"/clusters/{_cluster.name}/{_type}/{name}"
                matches = []
                if filter_query:
                    for cell in row["cells"]:
                        idx = str(cell).lower().find(filter_query_lower)
                        if idx > -1:
                            pre_start = max(idx - SEARCH_MATCH_CONTEXT_LENGTH, 0)
                            end = idx + len(filter_query_lower)
                            post_end = min(
                                idx
                                + len(filter_query_lower)
                                + SEARCH_MATCH_CONTEXT_LENGTH,
                                len(cell),
                            )
                            matches.append(
                                (cell[pre_start:idx], cell[idx:end], cell[end:post_end])
                            )
                            if len(matches) >= 3:
                                break
                results.append(
                    {
                        "title": name,
                        "kind": clazz.kind,
                        "link": link,
                        "matches": matches,
                        "labels": row["object"]["metadata"].get("labels", {}),
                        "created": row["object"]["metadata"]["creationTimestamp"],
                    }
                )
    except Exception as e:
        # just log as DEBUG because the error is shown in the web frontend already
        logger.debug(f"Failed to search {_type} in {_cluster.name}: {e}")
        errors.append({"cluster": _cluster, "resource_type": _type, "exception": e})

    return clazz, results, errors


async def bounded_search(
    semaphore,
    request,
    session,
    selector,
    filter_query,
    _type,
    _cluster,
    namespace,
    is_all_namespaces,
):
    async with semaphore:
        return await search(
            request,
            session,
            selector,
            filter_query,
            _type,
            _cluster,
            namespace,
            is_all_namespaces,
        )


def sort_rank(result, search_query_lower):
    score = 0

    if search_query_lower in result["title"].lower():
        if len(search_query_lower) == len(result["title"]):
            # equal
            score += 10
        else:
            score += 2

    if search_query_lower in result["labels"].values():
        score += 1

    return (-score, result["title"], result["kind"], result["link"])


@routes.get("/search")
@aiohttp_jinja2.template("search.html")
@context()
async def get_search(request, session):
    params = request.rel_url.query
    cluster = ",".join(params.getall("cluster", []))
    namespace = ",".join(params.getall("namespace", []))
    selector = params.get("selector", "").strip()
    search_query = params.get("q", "").strip()

    # k=v pairs in query will be changed to selector automatically
    selector_words = []
    filter_words = []
    for word in search_query.split():
        if "=" in word:
            selector_words.append(word)
        else:
            filter_words.append(word)

    selector += ",".join(selector_words)
    filter_query = " ".join(filter_words)

    default_resource_types = (
        request.app[CONFIG].search_default_resource_types
        or SEARCH_DEFAULT_RESOURCE_TYPES
    )

    resource_types = params.getall("type", None)
    if not resource_types:
        # note that ReplicaSet, DaemonSet, Pod, and Node are not included by default
        # as they are usually less relevant for search queries
        resource_types = default_resource_types

    clusters, is_all_clusters = get_clusters(request, cluster)

    is_all_namespaces = not namespace or namespace == ALL

    offered_resource_types = (
        request.app[CONFIG].search_offered_resource_types
        or SEARCH_OFFERED_RESOURCE_TYPES
    )
    searchable_resource_types = {}

    results = []
    errors_by_cluster = collections.defaultdict(list)

    start = time.time()

    # limit concurrency in case we have many clusters and search many resource types
    semaphore = asyncio.Semaphore(request.app[CONFIG].search_max_concurrency)

    # snapshot1 = tracemalloc.take_snapshot()

    tasks = []

    search_query_lower = search_query.lower()

    for _type in resource_types:
        for _cluster in clusters:
            task = asyncio.create_task(
                bounded_search(
                    semaphore,
                    request,
                    session,
                    selector,
                    filter_query,
                    _type,
                    _cluster,
                    namespace,
                    is_all_namespaces,
                )
            )
            tasks.append(task)

    if search_query and is_all_clusters:
        for _cluster in request.app[CLUSTER_MANAGER].clusters:
            is_match = search_query_lower in _cluster.name.lower()
            if not is_match:
                for key, val in _cluster.labels.items():
                    if search_query_lower in val.lower():
                        is_match = True
                        break
            if is_match:
                results.append(
                    {
                        "title": _cluster.name,
                        "kind": "Cluster",
                        "link": f"/clusters/{_cluster.name}",
                        "labels": _cluster.labels,
                        "created": None,
                    }
                )

    for clazz, _results, _errors in await asyncio.gather(*tasks):
        if clazz and clazz.endpoint not in searchable_resource_types:
            # search was done with a non-standard resource type (e.g. CRD)
            searchable_resource_types[clazz.endpoint] = clazz.kind
        results.extend(_results)
        for error in _errors:
            errors_by_cluster[error["cluster"].name].append(error)

    for resource_type in offered_resource_types:
        if resource_type not in searchable_resource_types:
            try:
                for i, _cluster in enumerate(clusters):
                    try:
                        clazz = await _cluster.resource_registry.get_class_by_plural_name(
                            resource_type, True, default=None
                        )
                        if not clazz:
                            clazz = await _cluster.resource_registry.get_class_by_plural_name(
                                resource_type, False
                            )
                    except:
                        if i >= len(clusters) - 1:
                            raise
                    else:
                        searchable_resource_types[clazz.endpoint] = clazz.kind
                        break
            except Exception as e:
                logger.warning(
                    f"Could not find resource type {resource_type} in one of the clusters: {e}"
                )

    results.sort(key=partial(sort_rank, search_query_lower=search_query_lower))

    # snapshot2 = tracemalloc.take_snapshot()
    # top_stats = snapshot2.compare_to(snapshot1, "lineno")

    # print("[ Top 10 differences ]")
    # for stat in top_stats[:10]:
    #    print(stat)

    duration = time.time() - start

    return {
        "cluster": cluster,
        "namespace": namespace,
        "search_results": results,
        "search_errors": errors_by_cluster,
        "search_query": search_query,
        "search_clusters": clusters,
        "search_duration": duration,
        "resource_types": resource_types,
        "searchable_resource_types": searchable_resource_types,
        "is_all_clusters": is_all_clusters,
        "is_all_namespaces": is_all_namespaces,
    }


@routes.get(HEALTH_PATH)
async def get_health(request):
    return web.Response(text="OK")


async def get_oauth2_client():
    authorize_url = URL(os.getenv("OAUTH2_AUTHORIZE_URL"))
    access_token_url = URL(os.getenv("OAUTH2_ACCESS_TOKEN_URL"))

    client_id = os.getenv("OAUTH2_CLIENT_ID")
    client_secret = os.getenv("OAUTH2_CLIENT_SECRET")

    client_id_file = os.getenv("OAUTH2_CLIENT_ID_FILE")
    if client_id_file:
        client_id = open(client_id_file).read().strip()
    client_secret_file = os.getenv("OAUTH2_CLIENT_SECRET_FILE")
    if client_secret_file:
        client_secret = open(client_secret_file).read().strip()

    # workaround for a bug in OAuth2Client where the authorize URL won't work with params ("?..")
    authorize_url_without_query = str(authorize_url.with_query(None))
    client = OAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        authorize_url=authorize_url_without_query,
        access_token_url=access_token_url,
    )
    return client, dict(authorize_url.query)


@web.middleware
async def auth(request, handler):
    path = request.rel_url.path
    if path == OAUTH2_CALLBACK_PATH:
        client, _ = await get_oauth2_client()
        # Get access token
        code = request.query["code"]
        try:
            state = json.loads(request.query["state"])
            original_url = state["url"]
        except:
            original_url = "/"
        redirect_uri = str(request.url.with_path(OAUTH2_CALLBACK_PATH))
        access_token, data = await client.get_access_token(
            code, redirect_uri=redirect_uri
        )
        expires_in = data.get("expires_in", ONE_WEEK)
        expires = time.time() + expires_in
        session = await get_session(request)
        hook = request.app[CONFIG].oauth2_authorized_hook
        if hook:
            # the hook can store additional stuff in the session,
            # deny access (raise exception), etc
            if not await hook(data, session):
                raise web.HTTPForbidden(text="Access Denied")
        session["access_token"] = access_token
        session["expires"] = expires
        raise web.HTTPFound(location=original_url)
    elif path != HEALTH_PATH:
        session = await get_session(request)
        # already expire session 5 minutes before actual expiry date
        # to make sure the access token is still valid during the request
        if (
            not session.get("access_token")
            or session.get("expires", 0) < time.time() + FIVE_MINUTES
        ):
            client, params = await get_oauth2_client()
            # note that Google OAuth provider requires the redirect_uri here
            # (it's optional according to https://tools.ietf.org/html/rfc6749#section-4.1.1)
            redirect_uri = str(request.url.with_path(OAUTH2_CALLBACK_PATH))
            params["redirect_uri"] = redirect_uri
            params["state"] = json.dumps({"url": str(request.rel_url)})
            raise web.HTTPFound(location=client.get_authorize_url(**params))
    response = await handler(request)
    return response


@web.middleware
async def error_handler(request, handler):
    try:
        response = await handler(request)
        return response
    except web.HTTPRedirection:
        # handling of redirection (3xx) is done by aiohttp itself
        raise
    except Exception as e:
        logger.debug(f"Exception on {request.rel_url}: {e}")
        if isinstance(e, web.HTTPError):
            status = e.status
            error_title = "Error"
            error_text = e.text
        elif isinstance(e, ClusterNotFound):
            status = 404
            error_title = "Error: cluster not found"
            error_text = f'Cluster "{e.cluster}" not found'
        elif isinstance(e, ResourceTypeNotFound):
            status = 404
            error_title = "Error: resource type not found"
            error_text = str(e)
        elif isinstance(e, ObjectDoesNotExist):
            status = 404
            error_title = "Error: object does not exist"
            error_text = "The requested Kubernetes object does not exist"
        elif isinstance(e, requests.exceptions.HTTPError):
            if e.response is not None and e.response.status_code in (401, 403):
                status = e.response.status_code
                error_title = HTTPStatus(status).phrase
                error_text = str(e)
            else:
                status = 500
                error_title = "Server Error"
                error_text = str(e)
                logger.exception(f"{error_title}: {error_text}")
        elif isinstance(e, pykube.exceptions.HTTPError):
            # Pykube exception is raised on get_by_name
            if e.code in (401, 403):
                status = e.code
                error_title = HTTPStatus(status).phrase
                error_text = str(e)
            else:
                status = 500
                error_title = "Server Error"
                error_text = str(e)
                logger.exception(f"{error_title}: {error_text}")
        else:
            status = 500
            error_title = "Server Error"
            error_text = str(e)
            logger.exception(f"{error_title}: {error_text}")

        context = {
            "error_title": error_title,
            "error_text": error_text,
            "status": status,
        }
        response = aiohttp_jinja2.render_template(
            "error.html", request, context, status=status
        )
        return response


def get_app(cluster_manager, config):
    templates_paths = [str(Path(__file__).parent / "templates")]
    if config.templates_path:
        # prepend the custom template path so custom templates will overwrite any default ones
        templates_paths.insert(0, config.templates_path)

    static_assets_path = Path(__file__).parent / "templates" / "assets"
    if config.static_assets_path:
        # overwrite assets path
        static_assets_path = Path(config.static_assets_path)

    object_links = collections.defaultdict(list)
    if config.object_links:
        for link_def in config.object_links.split(","):
            resource_type, sep, url_template = link_def.partition("=")
            object_links[resource_type].append(
                {
                    "href": url_template,
                    "title": "External link for object {name}",
                    "icon": "external-link-alt",
                }
            )

    label_links = collections.defaultdict(list)
    if config.label_links:
        for link_def in config.label_links.split(","):
            label, sep, url_template = link_def.partition("=")
            label_links[label].append(
                {
                    "href": url_template,
                    "title": "External link for {label} label with value '{label_value}'",
                    "icon": "external-link-alt",
                }
            )

    app = web.Application()
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(templates_paths),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env = aiohttp_jinja2.get_env(app)
    env.filters.update(
        pluralize=jinja2_filters.pluralize,
        yaml=jinja2_filters.yaml,
        highlight=jinja2_filters.highlight,
        age_color=jinja2_filters.age_color,
        cpu=jinja2_filters.cpu,
        memory=jinja2_filters.memory,
    )
    env.globals["version"] = __version__
    env.globals["object_links"] = object_links
    env.globals["label_links"] = label_links

    app.add_routes(routes)
    app.router.add_static("/assets", static_assets_path)

    # behind proxy
    app.middlewares.append(XForwardedRelaxed().middleware)

    secret_key = os.getenv("SESSION_SECRET_KEY") or Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(secret_key)
    session_setup(app, EncryptedCookieStorage(secret_key, cookie_name="KUBE_WEB_VIEW"))

    authorize_url = os.getenv("OAUTH2_AUTHORIZE_URL")
    access_token_url = os.getenv("OAUTH2_ACCESS_TOKEN_URL")

    if authorize_url and access_token_url:
        logger.info(
            f"Using OAuth2 middleware with authorization endpoint {authorize_url}"
        )
        app.middlewares.append(auth)

    app.middlewares.append(error_handler)

    app[CLUSTER_MANAGER] = cluster_manager
    app[CONFIG] = config

    return app
