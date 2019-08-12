import asyncio
import logging
from pykube.objects import APIObject, NamespacedAPIObject
from kube_web import kubernetes

logger = logging.getLogger(__name__)

throw_exception = object()


class ResourceTypeNotFound(Exception):
    def __init__(self, resource_type: str, namespaced: bool):
        super().__init__(
            f"{'Namespaced' if namespaced else 'Cluster'} resource type '{resource_type}' not found"
        )


async def discover_api_group(api, group_version, pref_version):
    logger.debug(f"Collecting resources for {group_version}..")
    response = await kubernetes.api_get(api, version=group_version)
    response.raise_for_status()
    return group_version, pref_version, response.json()["resources"]


async def discover_api_resources(api):
    core_version = "v1"
    r = await kubernetes.api_get(api, version=core_version)
    r.raise_for_status()
    for resource in r.json()["resources"]:
        # ignore subresources like pods/proxy
        if (
            "/" not in resource["name"]
            and "get" in resource["verbs"]
            and "list" in resource["verbs"]
        ):
            yield resource["namespaced"], core_version, resource

    r = await kubernetes.api_get(api, version="/apis")
    r.raise_for_status()
    tasks = []
    for group in r.json()["groups"]:
        pref_version = group["preferredVersion"]["groupVersion"]
        for version in group["versions"]:
            group_version = version["groupVersion"]
            tasks.append(
                asyncio.create_task(
                    discover_api_group(api, group_version, pref_version)
                )
            )

    yielded = set()
    non_preferred = []
    for group_version, pref_version, resources in await asyncio.gather(*tasks):
        for resource in resources:
            if (
                "/" not in resource["name"]
                and "get" in resource["verbs"]
                and "list" in resource["verbs"]
            ):
                if group_version == pref_version:
                    yield resource["namespaced"], group_version, resource
                    yielded.add((group_version, resource["name"]))
                else:
                    non_preferred.append(
                        (resource["namespaced"], group_version, resource)
                    )

    for namespaced, group_version, resource in non_preferred:
        if (group_version, resource["name"]) not in yielded:
            yield namespaced, group_version, resource


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


async def get_namespaced_resource_types(api):
    logger.debug(f"Getting resource types for {api.url}..")
    async for namespaced, api_version, resource in discover_api_resources(api):
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


class ResourceRegistry:
    def __init__(self, api):
        self.api = api
        self._lock = asyncio.Lock()
        self._cluster_resource_types = []
        self._namespaced_resource_types = []

    async def initialize(self):
        async with self._lock:
            if self._namespaced_resource_types and self._cluster_resource_types:
                # already initialized!
                return
            logger.info(f"Initializing resource registry for {self.api.url}..")
            namespaced_resource_types = []
            cluster_resource_types = []
            async for clazz in get_namespaced_resource_types(self.api):
                if issubclass(clazz, NamespacedAPIObject):
                    namespaced_resource_types.append(clazz)
                else:
                    cluster_resource_types.append(clazz)
            self._namespaced_resource_types = namespaced_resource_types
            self._cluster_resource_types = cluster_resource_types

    @property
    async def cluster_resource_types(self):
        if not self._cluster_resource_types:
            await self.initialize()
        return self._cluster_resource_types

    @property
    async def namespaced_resource_types(self):
        if not self._namespaced_resource_types:
            await self.initialize()
        return self._namespaced_resource_types

    async def get_class_by_plural_name(
        self, plural: str, namespaced: bool, default=throw_exception
    ):
        _types = (
            self.namespaced_resource_types
            if namespaced
            else self.cluster_resource_types
        )
        clazz = None
        for c in await _types:
            if c.endpoint == plural:
                clazz = c
                break
        if not clazz and default is throw_exception:
            raise ResourceTypeNotFound(plural, namespaced)
        return clazz

    async def get_class_by_api_version_kind(
        self, api_version: str, kind: str, namespaced: bool, default=throw_exception
    ):
        _types = (
            self.namespaced_resource_types
            if namespaced
            else self.cluster_resource_types
        )
        clazz = None
        for c in await _types:
            if c.version == api_version and c.kind == kind:
                clazz = c
                break
        if not clazz and default is throw_exception:
            raise ResourceTypeNotFound(kind, namespaced)
        return clazz
