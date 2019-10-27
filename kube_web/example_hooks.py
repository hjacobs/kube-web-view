"""
This file contains example hook functions for Kubernetes Web Web
"""


async def resource_view_prerender(cluster, namespace, resource, context):
    """
    Example hook function for the resource view page. Adds a link (icon button) for deployments.

    Usage: --resource-view-prerender-hook=kube_web.example_hooks.resource_view_prerender
    """
    if resource.kind == "Deployment":
        link = {
            "href": f"#this-is-a-custom-link;name={resource.name}",
            "class": "is-link",
            "title": "Some example link to nowhere",
            "icon": "external-link-alt",
        }
        context["links"].append(link)
