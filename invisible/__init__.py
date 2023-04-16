from invisible.app import TypedApp
from invisible.routes import bootstrap_routers
from pymongo import ASCENDING, TEXT


def initialize_application():
    app = TypedApp()
    bootstrap_routers(app)

    @app.on_event("startup")
    async def _on_startup():
        await app.database["tinyurl"].create_index(
            [("tiny_url", ASCENDING), ("url", ASCENDING)]
        )
        await app.database["host_metrics"].create_index([("host", TEXT)])
        app.producer = app.producer()
        await app.producer.start()

    return app
