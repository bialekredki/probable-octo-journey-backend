from pymongo import ASCENDING, TEXT
from pymongo.collation import (
    Collation,
    CollationAlternate,
    CollationMaxVariable,
    CollationStrength,
)

from app.app import TypedApp
from app.routes import bootstrap_routers


def initialize_application():
    app = TypedApp()
    bootstrap_routers(app)

    @app.on_event("startup")
    async def _on_startup():
        await app.database["tinyurl"].create_index(
            [("tiny_url", ASCENDING), ("url", ASCENDING)], unique=True
        )
        collation = Collation(
            locale="simple",
            alternate=CollationAlternate.NON_IGNORABLE,
            maxVariable=CollationMaxVariable.SPACE,
            strength=CollationStrength.PRIMARY,
        )
        await app.database["host_metrics"].create_index(
            [("search", TEXT)], collation=collation
        )
        await app.database["path_metrics"].create_index(
            [("search", TEXT)], collation=collation
        )
        await app.database["path_metrics"].create_index(
            [("url", ASCENDING)], unique=True
        )
        await app.database["host_metrics"].create_index(
            [("host", ASCENDING)], unique=True
        )
        app.producer = app.producer()
        await app.producer.start()

    return app
