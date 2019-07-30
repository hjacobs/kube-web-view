import aiohttp.web
import argparse
from .web import get_app
from .cluster_manager import ClusterManager
from kube_web import __version__

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
    "--show-container-logs",
    action="store_true",
    help="Enable container logs (hidden by default as they can contain sensitive information)",
)

args = parser.parse_args()

cluster_manager = ClusterManager(args.kubeconfig_path)
app = get_app(cluster_manager, args)
aiohttp.web.run_app(app, port=args.port)
