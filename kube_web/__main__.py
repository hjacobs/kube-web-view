import aiohttp_jinja2
import jinja2
import pykube
import logging

from pykube.objects import APIObject, NamespacedAPIObject

from pathlib import Path

from aiohttp import web

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


try:
    api = pykube.HTTPClient(pykube.KubeConfig.from_service_account())
except:
    api = pykube.HTTPClient(pykube.KubeConfig.from_file())


def discover_api_resources(api):
    core_version = "v1"
    r = api.get(version=core_version)
    r.raise_for_status()
    for resource in r.json()["resources"]:
        # ignore subresources like pods/proxy
        if "/" not in resource["name"]:
            yield resource["namespaced"], core_version, resource

    r = api.get(version="/apis")
    r.raise_for_status()
    for group in r.json()["groups"]:
        pref_version = group["preferredVersion"]["groupVersion"]
        logger.debug(f"Collecting resources for {pref_version}..")
        r2 = api.get(version=pref_version)
        r2.raise_for_status()
        for resource in r2.json()["resources"]:
            if "/" not in resource["name"]:
                yield resource["namespaced"], pref_version, resource


def cluster_object_factory(kind: str, name: str, api_version: str):
    # https://github.com/kelproject/pykube/blob/master/pykube/objects.py#L138
    return type(
        kind, (APIObject,), {"version": api_version, "endpoint": name, "kind": kind}
    )


def namespaced_object_factory(kind: str, name: str, api_version: str):
    # https://github.com/kelproject/pykube/blob/master/pykube/objects.py#L138
    return type(
        kind,
        (NamespacedAPIObject,),
        {"version": api_version, "endpoint": name, "kind": kind},
    )


def get_namespaced_resource_types(api):
    for namespaced, api_version, resource in discover_api_resources(api):
        if namespaced:
            clazz = namespaced_object_factory(
                resource["kind"], resource["name"], api_version
            )
            yield clazz
        else:
            clazz = cluster_object_factory(
                resource["kind"], resource["name"], api_version
            )
            yield clazz


cluster_resource_types = []
namespaced_resource_types = []

for clazz in get_namespaced_resource_types(api):
    if issubclass(clazz, NamespacedAPIObject):
        namespaced_resource_types.append(clazz)
    else:
        cluster_resource_types.append(clazz)

routes = web.RouteTableDef()


@routes.get("/")
@aiohttp_jinja2.template("index.html")
async def get_index(request):
    return {}


@routes.get("/clusters")
@aiohttp_jinja2.template("clusters.html")
async def get_index(request):
    return {}


@routes.get("/clusters/{cluster}/{plural}")
@aiohttp_jinja2.template("cluster-resource-list.html")
async def get_cluster_resource_list(request):
    cluster = request.match_info["cluster"]
    plural = request.match_info["plural"]
    clazz = None
    for c in cluster_resource_types:
        if c.endpoint == plural:
            clazz = c
            break
    if not clazz:
        return web.Response(status=404, text="Resource type not found")
    resources = list(clazz.objects(api).filter())
    return {"cluster": cluster, "plural": plural, "resources": resources}


@routes.get("/clusters/{cluster}/namespaces/{namespace}")
@aiohttp_jinja2.template("namespace.html")
async def get_namespace(request):
    cluster = request.match_info["cluster"]
    namespace = request.match_info["namespace"]
    return {"cluster": cluster, "namespace": namespace, "resource_types": namespaced_resource_types}


@routes.get("/clusters/{cluster}/namespaces/{namespace}/{plural}")
@aiohttp_jinja2.template("namespaced-resource-list.html")
async def get_namespaced_resource_list(request):
    cluster = request.match_info["cluster"]
    namespace = request.match_info["namespace"]
    plural = request.match_info["plural"]
    clazz = None
    for c in namespaced_resource_types:
        if c.endpoint == plural:
            clazz = c
            break
    if not clazz:
        return web.Response(status=404, text="Resource type not found")
    resources = list(clazz.objects(api).filter(namespace=namespace))
    return {"cluster": cluster, "namespace": namespace, "plural": plural, "resources": resources}


app = web.Application()
aiohttp_jinja2.setup(
    app, loader=jinja2.FileSystemLoader(str(Path(__file__).parent / "templates"))
)

app.add_routes(routes)
app.router.add_static("/assets", Path(__file__).parent / "templates" / "assets")

web.run_app(app)
