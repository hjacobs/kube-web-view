#!/usr/bin/env python3
"""
Example implementation of REST endpoint for a Cluster Registry.

To be used with --cluster-registry-url option
"""

from aiohttp import web

KUBERNETES_CLUSTERS = [
    {
        "id": "123",
        "alias": "foo",
        "api_server_url": "https://cluster-123.example.org",
        "channel": "stable",
        "environment": "production",
        "infrastructure_account": "aws:123456789012",
        "region": "eu-central-1",
        "lifecycle_status": "ready",
    },
    {
        "id": "123",
        "alias": "bar",
        "api_server_url": "https://cluster-456.example.org",
        "channel": "beta",
        "environment": "test",
        "infrastructure_account": "aws:123456789012",
        "region": "eu-central-1",
        "lifecycle_status": "ready",
    },
]

routes = web.RouteTableDef()


@routes.get("/kubernetes-clusters")
async def get_clusters(request):
    return web.json_response({"items": KUBERNETES_CLUSTERS})


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=8081)
