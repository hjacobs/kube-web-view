import asyncio
import logging
from pykube.objects import APIObject, NamespacedAPIObject
from kube_web import kubernetes

logger = logging.getLogger(__name__)


async def discover_api_group(api, group, group_version, pref_version):
    logger.debug(f"Collecting resources for {group_version}..")
    response = await kubernetes.api_get(api, version=group_version)
    response.raise_for_status()
    return group, group_version, pref_version, response.json()["resources"]


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
        print(group)
        pref_version = group["preferredVersion"]["groupVersion"]
        for version in group["versions"]:
            group_version = version["groupVersion"]
            tasks.append(
                asyncio.create_task(
                    discover_api_group(api, group["name"], group_version, pref_version)
                )
            )

    yielded = set()
    non_preferred = []
    for group, group_version, pref_version, resources in await asyncio.gather(*tasks):
        for resource in resources:
            if (
                "/" not in resource["name"]
                and "get" in resource["verbs"]
                and "list" in resource["verbs"]
            ):
                if group_version == pref_version:
                    yield resource["namespaced"], group_version, resource
                    yielded.add((group, resource["name"]))
                else:
                    non_preferred.append(
                        (group, resource["namespaced"], group_version, resource)
                    )

    for group, namespaced, group_version, resource in non_preferred:
        if (group, resource["name"]) not in yielded:
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
        self._cluster_resource_types = []
        self._namespaced_resource_types = []

    async def initialize(self):
        async for clazz in get_namespaced_resource_types(self.api):
            if issubclass(clazz, NamespacedAPIObject):
                self._namespaced_resource_types.append(clazz)
            else:
                self._cluster_resource_types.append(clazz)

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

    async def get_class_by_plural_name(self, plural: str, namespaced: bool):
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
        return clazz
