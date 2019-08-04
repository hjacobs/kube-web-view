from pykube.query import Query
from pykube.http import HTTPClient
from pykube.objects import Pod
from functools import partial
import asyncio

import concurrent.futures

thread_pool = concurrent.futures.ThreadPoolExecutor(thread_name_prefix="pykube")


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
