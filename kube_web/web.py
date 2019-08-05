import asyncio
import aiohttp_jinja2
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
from yarl import URL
import yaml

from functools import partial

from pykube import ObjectDoesNotExist
from pykube.objects import NamespacedAPIObject, Namespace, Event, Pod
from aiohttp_session import get_session, setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_remotes import XForwardedRelaxed
from aioauth_client import OAuth2Client
from cryptography.fernet import Fernet

from .cluster_manager import ClusterNotFound

from pathlib import Path

from aiohttp import web

from kube_web import __version__
from kube_web import kubernetes
from kube_web import jinja2_filters
from .table import add_label_columns, filter_table, sort_table

logger = logging.getLogger(__name__)

HEALTH_PATH = "/health"
OAUTH2_CALLBACK_PATH = "/oauth2/callback"

CLUSTER_MANAGER = "cluster_manager"
CONFIG = "config"


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
        "Status": {
            "Completed": "has-text-info",
            "Evicted": "has-text-danger",
            "OutOfcpu": "has-text-danger",
            "CrashLoopBackOff": "has-text-danger",
            "CreateContainerConfigError": "has-text-danger",
            "Error": "has-text-danger",
            "ErrImagePull": "has-text-danger",
            "ImagePullBackOff": "has-text-danger",
            "Pending": "has-text-warning",
            "Running": "has-text-success",
        }
    },
}


routes = web.RouteTableDef()


def context():
    def decorator(func):
        async def func_wrapper(request):
            ctx = await func(request)
            if isinstance(ctx, dict) and ctx.get("cluster"):
                if ctx["cluster"] != "_all":
                    cluster = request.app[CLUSTER_MANAGER].get(ctx["cluster"])
                    namespaces = await kubernetes.get_list(
                        Namespace.objects(cluster.api)
                    )
                    ctx["namespaces"] = namespaces
                ctx["rel_url"] = request.rel_url
            return ctx

        return func_wrapper

    return decorator


@routes.get("/")
async def get_index(request):
    # we don't have anything to present on the homepage, so let's redirect to the cluster list
    raise web.HTTPFound(location="/clusters")


@routes.get("/clusters")
@aiohttp_jinja2.template("clusters.html")
async def get_clusters(request):
    return {
        "clusters": sorted(request.app[CLUSTER_MANAGER].clusters, key=lambda c: c.name)
    }


@routes.get("/clusters/{cluster}")
@aiohttp_jinja2.template("cluster.html")
@context()
async def get_cluster(request):
    cluster = request.app[CLUSTER_MANAGER].get(request.match_info["cluster"])
    namespaces = await kubernetes.get_list(Namespace.objects(cluster.api))
    return {
        "cluster": cluster.name,
        "namespace": None,
        "namespaces": namespaces,
        "resource_types": await cluster.resource_registry.cluster_resource_types,
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
async def get_cluster_resource_types(request):
    cluster = request.match_info["cluster"]
    is_all_clusters = cluster == "_all"
    if is_all_clusters:
        clusters = request.app[CLUSTER_MANAGER].clusters
    else:
        clusters = [request.app[CLUSTER_MANAGER].get(cluster)]
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


@routes.get("/clusters/{cluster}/{plural}")
@aiohttp_jinja2.template("resource-list.html")
@context()
async def get_cluster_resource_list(request):
    cluster = request.match_info["cluster"]
    is_all_clusters = cluster == "_all"
    if is_all_clusters:
        clusters = request.app[CLUSTER_MANAGER].clusters
    else:
        clusters = [request.app[CLUSTER_MANAGER].get(cluster)]
    plural = request.match_info["plural"]
    params = request.rel_url.query
    tables = []
    for _cluster in clusters:
        clazz = await _cluster.resource_registry.get_class_by_plural_name(
            plural, namespaced=False
        )
        if not clazz:
            raise web.HTTPNotFound(text="Resource type not found")

        query = clazz.objects(_cluster.api)
        if params.get("selector"):
            query = query.filter(selector=params["selector"])
        table = await kubernetes.get_table(query)
        add_label_columns(table, params.get("labelcols"))
        filter_table(table, params.get("filter"))
        sort_table(table, params.get("sort"))
        table.obj["cluster"] = _cluster
        tables.append(table)
    if params.get("download") == "tsv":
        return await download_tsv(request, tables[0])
    return {
        "cluster": cluster,
        "is_all_clusters": is_all_clusters,
        "namespace": None,
        "plural": plural,
        "tables": tables,
        "get_cell_class": get_cell_class,
    }


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
    if issubclass(table.api_obj_class, NamespacedAPIObject):
        writer.writerow(["Namespace"] + [col["name"] for col in table.columns])
    else:
        writer.writerow([col["name"] for col in table.columns])
    for row in table.rows:
        if issubclass(table.api_obj_class, NamespacedAPIObject):
            writer.writerow([row["object"]["metadata"]["namespace"]] + row["cells"])
        else:
            writer.writerow(row["cells"])
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
async def get_namespaced_resource_types(request):
    cluster = request.match_info["cluster"]
    is_all_clusters = cluster == "_all"
    if is_all_clusters:
        clusters = request.app[CLUSTER_MANAGER].clusters
    else:
        clusters = [request.app[CLUSTER_MANAGER].get(cluster)]
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


@routes.get("/clusters/{cluster}/namespaces/{namespace}/{plural}")
@aiohttp_jinja2.template("resource-list.html")
@context()
async def get_namespaced_resource_list(request):
    cluster = request.match_info["cluster"]
    is_all_clusters = cluster == "_all"
    if is_all_clusters:
        clusters = request.app[CLUSTER_MANAGER].clusters
    else:
        clusters = [request.app[CLUSTER_MANAGER].get(cluster)]
    namespace = request.match_info["namespace"]
    plural = request.match_info["plural"]

    is_all_namespaces = namespace == "_all"

    if plural == "all":
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

    params = request.rel_url.query
    tables = []
    for _type in resource_types:
        for _cluster in clusters:
            clazz = await _cluster.resource_registry.get_class_by_plural_name(
                _type, namespaced=True
            )
            if not clazz:
                raise web.HTTPNotFound(text="Resource type not found")
            query = clazz.objects(_cluster.api).filter(
                namespace=pykube.all if is_all_namespaces else namespace
            )
            if params.get("selector"):
                query = query.filter(selector=params["selector"])

            table = await kubernetes.get_table(query)
            add_label_columns(table, params.get("labelcols"))
            filter_table(table, params.get("filter"))
            sort_table(table, params.get("sort"))
            table.obj["cluster"] = _cluster
            tables.append(table)
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
    }


@routes.get("/clusters/{cluster}/{plural}/{name}")
@routes.get("/clusters/{cluster}/namespaces/{namespace}/{plural}/{name}")
@aiohttp_jinja2.template("resource-view.html")
@context()
async def get_resource_view(request):
    cluster = request.app[CLUSTER_MANAGER].get(request.match_info["cluster"])
    namespace = request.match_info.get("namespace")
    plural = request.match_info["plural"]
    name = request.match_info["name"]
    params = request.rel_url.query
    view = params.get("view")
    clazz = await cluster.resource_registry.get_class_by_plural_name(
        plural, namespaced=bool(namespace)
    )
    if not clazz:
        raise web.HTTPNotFound(text="Resource type not found")
    query = clazz.objects(cluster.api)
    if namespace:
        query = query.filter(namespace=namespace)
    resource = await kubernetes.get_by_name(query, name)

    if resource.kind == "Secret" and not request.app[CONFIG].show_secrets:
        # mask out all secret values, but still show keys
        for key in resource.obj["data"].keys():
            resource.obj["data"][key] = "**SECRET-CONTENT-HIDDEN-BY-KUBE-WEB-VIEW**"
        # the secret data is also leaked in annotations ("last-applied-configuration")
        # => hide annotations
        resource.metadata["annotations"] = {"annotations-hidden": "by-kube-web-view"}

    if params.get("download") == "yaml":
        return await download_yaml(request, resource)

    if resource.obj.get("spec", {}).get("selector", {}).get("matchLabels"):
        query = Pod.objects(cluster.api).filter(
            namespace=namespace,
            selector=resource.obj["spec"]["selector"]["matchLabels"],
        )
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
        Event.objects(cluster.api).filter(
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
async def get_resource_logs(request):
    cluster = request.app[CLUSTER_MANAGER].get(request.match_info["cluster"])
    namespace = request.match_info.get("namespace")
    plural = request.match_info["plural"]
    name = request.match_info["name"]
    tail_lines = int(request.rel_url.query.get("tail_lines") or 200)
    clazz = await cluster.resource_registry.get_class_by_plural_name(
        plural, namespaced=True
    )
    if not clazz:
        raise web.HTTPNotFound(text="Resource type not found")
    query = clazz.objects(cluster.api)
    if namespace:
        query = query.filter(namespace=namespace)
    resource = await kubernetes.get_by_name(query, name)

    if resource.kind == "Pod":
        pods = [resource]
    elif resource.obj.get("spec", {}).get("selector", {}).get("matchLabels"):
        query = Pod.objects(cluster.api).filter(
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


async def search(search_query, _type, _cluster, namespace, is_all_namespaces):
    clazz = None
    results = []
    errors = []
    try:
        namespaced = True
        clazz = await _cluster.resource_registry.get_class_by_plural_name(
            _type, namespaced=True
        )
        if not clazz:
            clazz = await _cluster.resource_registry.get_class_by_plural_name(
                _type, namespaced=False
            )
            if not clazz:
                raise web.HTTPNotFound(text=f"Resource type '{_type}' not found")
            namespaced = False
        query = clazz.objects(_cluster.api)
        if namespaced:
            query = query.filter(
                namespace=pykube.all if is_all_namespaces else namespace
            )

        table = await kubernetes.get_table(query)
    except Exception as e:
        errors.append({"cluster": _cluster, "resource_type": _type, "exception": e})
    else:
        add_label_columns(table, "*")
        filter_table(table, search_query)
        name_column = 0
        for i, col in enumerate(table.columns):
            if col["name"] == "Name":
                name_column = i
                break
        for row in table.rows:
            name = row["cells"][name_column]
            if namespaced:
                ns = row["object"]["metadata"]["namespace"]
                link = f"/clusters/{_cluster.name}/namespaces/{ns}/{_type}/{name}"
            else:
                link = f"/clusters/{_cluster.name}/{_type}/{name}"
            results.append(
                {
                    "title": name,
                    "kind": clazz.kind,
                    "link": link,
                    "labels": row["object"]["metadata"].get("labels", {}),
                    "created": row["object"]["metadata"]["creationTimestamp"],
                }
            )
    return clazz, results, errors


def sort_rank(result, search_query_lower):
    score = 0
    if search_query_lower in result["title"].lower():
        score += 2

    if search_query_lower in result["labels"].values():
        score += 1

    return (-score, result["title"], result["kind"], result["link"])


@routes.get("/search")
@aiohttp_jinja2.template("search.html")
@context()
async def get_search(request):
    params = request.rel_url.query
    cluster = params.get("cluster")
    namespace = params.get("namespace")
    search_query = params.get("q", "").strip()
    resource_types = params.getall("type", None)
    if not resource_types:
        # note that ReplicaSet, Pod, and Node are not included by default
        # as they are usually less relevant for search queries
        resource_types = [
            "namespaces",
            "deployments",
            "services",
            "ingresses",
            "daemonsets",
            "statefulsets",
            "cronjobs",
        ]

    is_all_clusters = not bool(cluster)
    if is_all_clusters:
        clusters = request.app[CLUSTER_MANAGER].clusters
    else:
        clusters = [request.app[CLUSTER_MANAGER].get(cluster)]

    is_all_namespaces = not namespace or namespace == "_all"

    searchable_resource_types = {
        "namespaces": "Namespace",
        "deployments": "Deployment",
        "replicasets": "ReplicaSet",
        "services": "Service",
        "ingresses": "Ingress",
        "daemonsets": "DaemonSet",
        "statefulsets": "StatefulSet",
        "cronjobs": "CronJob",
        "pods": "Pod",
        "nodes": "Node",
    }

    results = []
    errors = []

    start = time.time()

    if search_query:
        tasks = []

        for _type in resource_types:
            for _cluster in clusters:
                task = asyncio.create_task(
                    search(search_query, _type, _cluster, namespace, is_all_namespaces)
                )
                tasks.append(task)

        for clazz, _results, _errors in await asyncio.gather(*tasks):
            if clazz.endpoint not in searchable_resource_types:
                # search was done with a non-standard resource type (e.g. CRD)
                searchable_resource_types[clazz.endpoint] = clazz.kind
            results.extend(_results)
            errors.extend(_errors)

        results.sort(key=partial(sort_rank, search_query_lower=search_query.lower()))

    duration = time.time() - start

    return {
        "cluster": cluster,
        "namespace": namespace,
        "search_results": results,
        "search_errors": errors,
        "search_query": search_query,
        "search_clusters": clusters,
        "search_duration": duration,
        "resource_types": resource_types,
        "searchable_resource_types": searchable_resource_types,
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
        session = await get_session(request)
        session["access_token"] = access_token
        raise web.HTTPFound(location=original_url)
    elif path != HEALTH_PATH:
        session = await get_session(request)
        if not session.get("access_token"):
            client, params = await get_oauth2_client()
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
        if isinstance(e, web.HTTPError):
            status = e.status
            error_title = "Error"
            error_text = e.text
        elif isinstance(e, ClusterNotFound):
            status = 404
            error_title = "Error: cluster not found"
            error_text = f'Cluster "{e.cluster}" not found'
        elif isinstance(e, ObjectDoesNotExist):
            status = 404
            error_title = "Error: object does not exist"
            error_text = "The requested Kubernetes object does not exist"
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
    )
    env.globals["version"] = __version__

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
        app.middlewares.append(auth)

    app.middlewares.append(error_handler)

    app[CLUSTER_MANAGER] = cluster_manager
    app[CONFIG] = config

    return app
