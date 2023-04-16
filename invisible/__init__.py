from invisible.app import TypedApp
from invisible.routes import bootstrap_routers
from pymongo import ASCENDING


def initialize_application():
    app = TypedApp()
    bootstrap_routers(app)

    @app.on_event("startup")
    async def _on_startup():
        await app.database["tinyurl"].create_index(
            [("tiny_url", ASCENDING), ("url", ASCENDING)]
        )

    return app
