import asyncio
import logging

import aiorun
import clickhouse_connect
from geoip2.database import Reader
from clickhouse_connect.driver import exceptions as clickhouse_exceptions
from motor.core import Database
from motor.motor_asyncio import AsyncIOMotorClient
from nanoid import generate

from app.config import configuration
from app.consumers import Consumer
from app.consumers.handlers import HandleAnalytics, HandleLastVisitTime, HandleMetrics
from app.consumers.middleware import (
    ExceptionMiddleware,
    LoggingMiddleware,
    OrJSONMiddleware,
    TimingMiddleware,
)


async def main():
    db_client = AsyncIOMotorClient(configuration.mongo_dsn)
    clickhouse_client = clickhouse_connect.get_client(host="clickhouse", password="")
    ip_reader = Reader("./GeoLite2-Country.mmdb")
    try:
        clickhouse_client.command(
            "CREATE TABLE analytics (host String, path String, tiny_url String, timestamp DateTime, ip_address String, location String, device String, operating_system String, browser String, is_mobile Bool, is_bot Bool) ENGINE = MergeTree() PRIMARY KEY (tiny_url, timestamp, ip_address)"
        )
    except clickhouse_exceptions.DatabaseError:
        pass
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
            "clickhouse_client": clickhouse_client,
            "ip_reader": ip_reader,
        },
    )

    consumer.declare_middleware(OrJSONMiddleware())
    consumer.declare_middleware(ExceptionMiddleware(logger))
    consumer.declare_middleware(TimingMiddleware(logger))
    consumer.declare_middleware(LoggingMiddleware(logger))

    consumer.declare_handler(HandleLastVisitTime(), "URL.read")
    consumer.declare_handler(HandleMetrics(), ("URL.read", "URL.create"))
    consumer.declare_handler(HandleAnalytics(), ("URL.read"))

    await consumer.run()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    aiorun.run(main(), loop=loop)
