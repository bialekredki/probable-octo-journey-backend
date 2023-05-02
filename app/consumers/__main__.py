import asyncio
import logging

import aioredis
import aiorun
from motor.core import Database
from motor.motor_asyncio import AsyncIOMotorClient
from nanoid import generate

from app.config import configuration
from app.consumers import Consumer
from app.consumers.handlers import HandleLastVisitTime, HandleMetrics
from app.consumers.middleware import (
    ExceptionMiddleware,
    LoggingMiddleware,
    OrJSONMiddleware,
    TimingMiddleware,
)


async def main():
    db_client = AsyncIOMotorClient(configuration.mongo_dsn)
    database: Database = db_client["test"]
    consumer_id = f"invisible-{generate(size=8)}"
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(consumer_id)

    consumer = Consumer(
        logger=logger,
        bootstrap_servers=f"{configuration.kafka_dsn.host}:{configuration.kafka_dsn.port}",
        client_id=consumer_id,
        services={
            "tinyurl_collection": database["tinyurl"],
            "host_metrics_collection": database["host_metrics"],
            "path_metrics_collection": database["path_metrics"],
        },
    )

    consumer.declare_middleware(OrJSONMiddleware())
    consumer.declare_middleware(ExceptionMiddleware(logger))
    consumer.declare_middleware(TimingMiddleware(logger))
    consumer.declare_middleware(LoggingMiddleware(logger))

    consumer.declare_handler(HandleLastVisitTime(), "URL.read")
    consumer.declare_handler(HandleMetrics(), ("URL.read", "URL.create"))

    await consumer.run()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    aiorun.run(main(), loop=loop)
