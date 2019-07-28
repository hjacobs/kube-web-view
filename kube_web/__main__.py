import aiohttp.web
import argparse
from .web import get_app
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

args = parser.parse_args()

app = get_app()
aiohttp.web.run_app(app, port=args.port)
