from fastapi import FastAPI

from app.routes.file import router as file_router
from app.routes.metrics import router as metrics_router
from app.routes.text import router as text_router
from app.routes.url import router as url_router


def bootstrap_routers(app: FastAPI):
    for router in (file_router, text_router, url_router, metrics_router):
        app.include_router(router)
