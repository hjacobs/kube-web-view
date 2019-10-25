import asyncio
import aiohttp.web
import argparse
import collections
import importlib
import logging
import re

from pathlib import Path

from kube_web import __version__
from .web import get_app
from .selector import parse_selector
from .cluster_discovery import (
    StaticClusterDiscoverer,
    ClusterRegistryDiscoverer,
    ServiceAccountClusterDiscoverer,
    ServiceAccountNotFound,
    KubeconfigDiscoverer,
)
from .cluster_manager import ClusterManager


logger = logging.getLogger(__name__)


def comma_separated_values(value):
    return list(filter(None, value.split(",")))


def comma_separated_patterns(value):
    return list(re.compile(p) for p in filter(None, value.split(",")))


def key_value_pairs(value):
    data = {}
    for kv_pair in value.split(";"):
        key, sep, value = kv_pair.partition("=")
        data[key] = value
    return data


def key_value_pairs2(value):
    data = {}
    for kv_pair in value.split(";;"):
        key, sep, value = kv_pair.partition("=")
        data[key] = value
    return data


def key_value_list_pairs(value):
    data = {}
    for kv_pair in value.split(";"):
        key, sep, value = kv_pair.partition("=")
        data[key] = comma_separated_values(value)
    return data


def coroutine_function(value):
    module_name, attr_path = value.rsplit(".", 1)
    module = importlib.import_module(module_name)
    function = getattr(module, attr_path)
    if not asyncio.iscoroutinefunction(function):
        raise ValueError(f"Not a coroutine (async) function: {value}")
    return function


def links_dict(value):
    links = collections.defaultdict(list)
    if value:
        for link_def in value.split(","):
            key, sep, url_template = link_def.partition("=")
            url_template, *options = url_template.split("|")
            icon, title, *rest = options + [None, None]
            links[key].append(
                {
                    "href": url_template,
                    "icon": icon or "external-link-alt",
                    "title": title or "External link",
                }
            )
    return links


def parse_args(argv=None):

    parser = argparse.ArgumentParser(description=f"Kubernetes Web View v{__version__}")
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="TCP port to start webserver on (default: 8080)",
    )
    parser.add_argument(
        "--version", action="version", version=f"kube-web-view {__version__}"
    )
    parser.add_argument(
        "--include-namespaces",
        type=comma_separated_patterns,
        help="List of namespaces to allow access to (default: all namespaces). Can be a comma-separated list of regex patterns.",
    )
    parser.add_argument(
        "--exclude-namespaces",
        type=comma_separated_patterns,
        help="List of namespaces to deny access to (default: none). Can be a comma-separated list of regex patterns.",
    )
    parser.add_argument(
        "--clusters",
        type=key_value_pairs,
        help="Cluster NAME=URL pairs separated by semicolon, e.g. 'foo=https://foo-api.example.org;bar=https://localhost:6443'",
    )
    parser.add_argument("--kubeconfig-path", help="Path to ~/.kube/config file")
    parser.add_argument(
        "--kubeconfig-contexts",
        type=comma_separated_values,
        help="List of kubeconfig contexts to use (default: use all defined contexts)",
    )
    parser.add_argument("--cluster-registry-url", help="URL to cluster registry")
    parser.add_argument(
        "--cluster-registry-oauth2-bearer-token-path",
        type=Path,
        help="Path to OAuth2 Bearer token for Cluster Registry authentication",
    )
    parser.add_argument(
        "--cluster-label-selector",
        type=parse_selector,
        help="Optional label selector to filter clusters, e.g. 'region=eu-central-1' would only load clusters with label 'region' equal 'eu-central-1'",
    )
    parser.add_argument(
        "--cluster-auth-token-path",
        type=Path,
        help="Path to file containing OAuth2 access Bearer token to use for cluster authentication",
    )
    parser.add_argument(
        "--cluster-auth-use-session-token",
        action="store_true",
        help="Use OAuth2 access token from frontend session for cluster authentication",
    )
    parser.add_argument(
        "--show-container-logs",
        action="store_true",
        help="Enable container logs (hidden by default as they can contain sensitive information)",
    )
    parser.add_argument(
        "--show-secrets",
        action="store_true",
        help="Show contents of Kubernetes Secrets (hidden by default as they contain sensitive information)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Run in debugging mode (log more)"
    )
    # customization options
    parser.add_argument(
        "--templates-path", help="Path to directory with custom HTML/Jinja2 templates"
    )
    parser.add_argument(
        "--static-assets-path",
        help="Path to custom JS/CSS assets (will be mounted as /assets HTTP path)",
    )
    parser.add_argument(
        "--object-links",
        type=links_dict,
        help="Comma-separated list of URL templates per resource type to link to external tools, e.g. 'pods=https://mymonitoringtool/{cluster}/{namespace}/{name}'",
    )
    parser.add_argument(
        "--label-links",
        type=links_dict,
        help="Comma-separated list of URL templates per label to link to external tools, e.g. 'application=https://myui/apps/{application}'",
    )
    parser.add_argument(
        "--sidebar-resource-types",
        type=key_value_list_pairs,
        help="Comma-separated list of resource types per category, e.g. 'Controllers=deployments,cronjobs;Pod Management=ingresses,pods'",
    )
    parser.add_argument(
        "--search-default-resource-types",
        type=comma_separated_values,
        help="Comma-separated list of resource types to use for navbar search by default, e.g. 'deployments,pods'",
    )
    parser.add_argument(
        "--search-offered-resource-types",
        type=comma_separated_values,
        help="Comma-separated list of resource types to offer on search page, e.g. 'deployments,pods,nodes'",
    )
    parser.add_argument(
        "--search-max-concurrency",
        type=int,
        help="Maximum number of current searches (across clusters/resource types), this allows limiting memory consumption and Kubernetes API calls (default: 100)",
        default=100,
    )
    parser.add_argument(
        "--default-label-columns",
        type=key_value_pairs,
        help="Comma-separated list of label columns per resource type; multiple entries separated by semicolon, e.g. 'pods=app,version;deployments=team'",
        default={},
    )
    parser.add_argument(
        "--default-hidden-columns",
        type=key_value_pairs,
        help="Comma-separated list of columns to hide per resource type; multiple entries separated by semicolon, e.g. 'pods=Nominated Node,Readiness Gates,version;deployments=Selector'",
        default={},
    )
    parser.add_argument(
        "--default-custom-columns",
        type=key_value_pairs2,
        help="Semicolon-separated list of Column=<expresion> pairs per resource type; multiple entries separated by two semicolons, e.g. 'pods=Images=spec.containers[*].image;;deployments=Replicas=spec.replicas'",
        default={},
    )
    parser.add_argument(
        "--oauth2-authorized-hook",
        type=coroutine_function,
        help="Optional hook (name of a coroutine like 'mymodule.myfunc') to process OAuth access token response (validate, log, ..)",
    )
    parser.add_argument(
        "--resource-view-prerender-hook",
        type=coroutine_function,
        help="Optional hook (name of a coroutine like 'mymodule.myfunc') to process/enrich template context for the resource detail view",
    )
    parser.add_argument(
        "--preferred-api-versions",
        type=key_value_pairs,
        help="Preferred Kubernetes apiVersion per resource type, e.g. 'horizontalpodautoscalers=autoscaling/v2beta2;deployments=apps/v1'",
        default={},
    )
    parser.add_argument(
        "--default-theme",
        help="Default CSS theme to use (default: default)",
        default="default",
    )
    parser.add_argument(
        "--theme-options",
        type=comma_separated_values,
        help="CSS themes the user can choose from (default: all themes)",
        default=[],
    )
    args = parser.parse_args(argv)
    return args


def main(argv=None):
    args = parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    config_str = ", ".join(f"{k}={v}" for k, v in sorted(vars(args).items()))
    logger.info(f"Kubernetes Web View v{__version__} started with {config_str}")

    if args.clusters:
        cluster_discoverer = StaticClusterDiscoverer(args.clusters)
    elif args.cluster_registry_url:
        cluster_discoverer = ClusterRegistryDiscoverer(
            args.cluster_registry_url, args.cluster_registry_oauth2_bearer_token_path
        )
    elif args.kubeconfig_path:
        cluster_discoverer = KubeconfigDiscoverer(
            args.kubeconfig_path, args.kubeconfig_contexts
        )
    else:
        # try to use in-cluster config
        try:
            cluster_discoverer = ServiceAccountClusterDiscoverer()
        except ServiceAccountNotFound:
            # fallback to default kubeconfig
            cluster_discoverer = KubeconfigDiscoverer(
                args.kubeconfig_path, args.kubeconfig_contexts
            )
    cluster_manager = ClusterManager(
        cluster_discoverer,
        args.cluster_label_selector,
        args.cluster_auth_token_path,
        args.preferred_api_versions,
    )
    app = get_app(cluster_manager, args)
    aiohttp.web.run_app(app, port=args.port, handle_signals=False)
