import asyncio
import logging
from functools import partial

import aioredis
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI
from fastapi.requests import Request
from motor.core import AgnosticClient, Database
from motor.motor_asyncio import AsyncIOMotorClient

from invisible.config import configuration


class TypedApp(FastAPI):
    logger: logging.Logger
    db_client: AgnosticClient
    database: Database
    redis: aioredis.Redis
    config = configuration

    def __init__(self, **kwargs) -> None:
        super().__init__(docs_url=None, redoc_url="/docs", **kwargs)
        self.logger = logging.getLogger(self.title)
        self.db_client = AsyncIOMotorClient(self.config.mongo_dsn)
        self.database = self.db_client["test"]
        self.redis = aioredis.from_url(self.config.redis_dsn)
        self.producer = partial(
            AIOKafkaProducer,
            bootstrap_servers=f"{self.config.kafka_dsn.host}:{self.config.kafka_dsn.port}",
        )


class TypedRequest(Request):
    app: TypedApp
