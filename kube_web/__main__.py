import aiohttp.web
from .web import get_app

app = get_app()
aiohttp.web.run_app(app)
