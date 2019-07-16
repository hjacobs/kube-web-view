import aiohttp_jinja2
import jinja2
import pykube

from pathlib import Path

from aiohttp import web

api = pykube.HTTPClient(pykube.KubeConfig.from_file())

@aiohttp_jinja2.template('index.html')
async def get_index(request):
    resources = list(pykube.Deployment.objects(api).filter(namespace='default'))
    return {'resources': resources}


app = web.Application()
aiohttp_jinja2.setup(app,
    loader=jinja2.FileSystemLoader(str(Path(__file__).parent / 'templates')))

app.add_routes(
    [
        web.get("/", get_index),
    ]
)

web.run_app(app)
