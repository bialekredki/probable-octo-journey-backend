import logging

from fastapi import FastAPI
from fastapi.requests import Request
from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import Database
from motor.core import AgnosticClient

from invisible.config import configuration


class TypedApp(FastAPI):
    logger: logging.Logger
    db_client: AgnosticClient
    database: Database
    config = configuration

    def __init__(self, **kwargs) -> None:
        super().__init__(docs_url=None, redoc_url="/docs", **kwargs)
        self.logger = logging.getLogger(self.title)
        self.db_client = AsyncIOMotorClient(self.config.mongo_dsn)
        self.database = self.db_client["test"]


class TypedRequest(Request):
    app: TypedApp