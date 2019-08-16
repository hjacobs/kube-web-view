import asyncio
import aiohttp.web
import argparse
import importlib
import logging

from pathlib import Path

from kube_web import __version__
from .web import get_app
from .selector import parse_selector
from .cluster_discovery import (
    ClusterRegistryDiscoverer,
    ServiceAccountClusterDiscoverer,
    ServiceAccountNotFound,
    KubeconfigDiscoverer,
)
from .cluster_manager import ClusterManager


logger = logging.getLogger(__name__)


def comma_separated_values(value):
    return list(filter(None, value.split(",")))


def key_value_pairs(value):
    data = {}
    for kv_pair in value.split(";"):
        key, sep, value = kv_pair.partition("=")
        data[key] = value
    return data


def coroutine_function(value):
    module_name, attr_path = value.rsplit(".", 1)
    module = importlib.import_module(module_name)
    function = getattr(module, attr_path)
    if not asyncio.iscoroutinefunction(function):
        raise ValueError(f"Not a coroutine (async) function: {value}")
    return function


def main(argv=None):

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
        help="Comma-separated list of URL templates per resource type to link to external tools, e.g. 'pods=https://mymonitoringtool/{cluster}/{namespace}/{name}'",
    )
    parser.add_argument(
        "--label-links",
        help="Comma-separated list of URL templates per label to link to external tools, e.g. 'application=https://myui/apps/{application}'",
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
        "--oauth2-authorized-hook",
        type=coroutine_function,
        help="Optional hook (name of a coroutine like 'mymodule.myfunc') to process OAuth access token response (validate, log, ..)",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    config_str = ", ".join(f"{k}={v}" for k, v in sorted(vars(args).items()))
    logger.info(f"Kubernetes Web View v{__version__} started with {config_str}")

    if args.cluster_registry_url:
        cluster_discoverer = ClusterRegistryDiscoverer(
            args.cluster_registry_url, args.cluster_registry_oauth2_bearer_token_path
        )
    else:
        try:
            cluster_discoverer = ServiceAccountClusterDiscoverer()
        except ServiceAccountNotFound:
            cluster_discoverer = KubeconfigDiscoverer(
                args.kubeconfig_path, args.kubeconfig_contexts
            )
    cluster_manager = ClusterManager(cluster_discoverer, args.cluster_label_selector)
    app = get_app(cluster_manager, args)
    aiohttp.web.run_app(app, port=args.port)
