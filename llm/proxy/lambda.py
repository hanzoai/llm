from mangum import Mangum
from llm.proxy.proxy_server import app

handler = Mangum(app, lifespan="on")
