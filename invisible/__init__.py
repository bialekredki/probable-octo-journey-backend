from invisible.app import TypedApp
from invisible.routes import bootstrap_routers


def initialize_application():
    app = TypedApp(docs_url=None, redoc_url="/docs")
    bootstrap_routers(app)
    return app
