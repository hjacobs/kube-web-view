import re

from pykube.query import Query
from pykube.http import HTTPClient
from pykube.objects import Pod, APIObject, NamespacedAPIObject
from functools import partial
import asyncio

import concurrent.futures

FACTORS = {
    "n": 1 / 1000000000,
    "u": 1 / 1000000,
    "m": 1 / 1000,
    "": 1,
    "k": 1000,
    "M": 1000 ** 2,
    "G": 1000 ** 3,
    "T": 1000 ** 4,
    "P": 1000 ** 5,
    "E": 1000 ** 6,
    "Ki": 1024,
    "Mi": 1024 ** 2,
    "Gi": 1024 ** 3,
    "Ti": 1024 ** 4,
    "Pi": 1024 ** 5,
    "Ei": 1024 ** 6,
}

RESOURCE_PATTERN = re.compile(r"^(\d*)(\D*)$")

thread_pool = concurrent.futures.ThreadPoolExecutor(thread_name_prefix="pykube")


# https://github.com/kubernetes/community/blob/master/contributors/design-proposals/instrumentation/resource-metrics-api.md
class NodeMetrics(APIObject):

    version = "metrics.k8s.io/v1beta1"
    endpoint = "nodes"
    kind = "NodeMetrics"


# https://github.com/kubernetes/community/blob/master/contributors/design-proposals/instrumentation/resource-metrics-api.md
class PodMetrics(NamespacedAPIObject):

    version = "metrics.k8s.io/v1beta1"
    endpoint = "pods"
    kind = "PodMetrics"


def parse_resource(v):
    """
    >>> parse_resource('100m')
    0.1
    >>> parse_resource('100M')
    1000000000
    >>> parse_resource('2Gi')
    2147483648
    >>> parse_resource('2k')
    2048
    """
    match = RESOURCE_PATTERN.match(v)
    factor = FACTORS[match.group(2)]
    return int(match.group(1)) * factor


async def api_get(api, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool, partial(HTTPClient.get, **kwargs), api
    )


async def get_by_name(query: Query, name: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, Query.get_by_name, query, name)


async def get_table(query: Query):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, Query.as_table, query)


def _get_list(query: Query):
    return list(query.iterator())


async def get_list(query: Query):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, _get_list, query)


async def logs(pod: Pod, **kwargs):
    loop = asyncio.get_event_loop()
    pod_logs = partial(Pod.logs, **kwargs)
    return await loop.run_in_executor(thread_pool, pod_logs, pod)
