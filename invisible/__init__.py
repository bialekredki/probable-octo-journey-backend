from invisible.app import TypedApp
from invisible.routes import bootstrap_routers


def initialize_application():
    app = TypedApp()
    bootstrap_routers(app)
    return app
