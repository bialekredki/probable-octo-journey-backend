import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime

from motor.core import Collection
from pymongo.collection import ReturnDocument

from invisible.consumers.utils import RecordT
from invisible.models import URL
from invisible.models.metrics import Host, Path


class BaseHandler(ABC):
    services: dict[str, Any]
    logger: logging.Logger

    def make_declared(self, consumer):
        self.services = consumer.services
        self.logger = consumer.logger
        self.parent = consumer

    def __str__(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    async def __call__(self, record: RecordT) -> Any:
        raise NotImplementedError()


class HandleLastVisitTime(BaseHandler):
    async def __call__(self, record: RecordT) -> Any:
        tiny_url_collection: Collection = self.services["tinyurl_collection"]
        url = await tiny_url_collection.find_one({"tiny_url": record.value["tiny_url"]})

        url = URL(**url)
        record_datetime = datetime.fromtimestamp(record.timestamp / 1000)
        if url.last_visit_time is None or record_datetime > url.last_visit_time:
            await tiny_url_collection.update_one(
                {"_id": url.id}, {"$set": {"last_visit_time": record_datetime}}
            )


class HandleMetrics(BaseHandler):
    async def __call__(self, record: RecordT) -> Any:
        host_metrics_collection: Collection = self.services["host_metrics_collection"]
        path_metrics_collection: Collection = self.services["path_metrics_collection"]

        url = URL(**record.value)

        host_metrics, path_metrics = await asyncio.gather(
            *[
                host_metrics_collection.find_one({"host": url.url.host}),
                path_metrics_collection.find_one({"url": url.url}),
            ]
        )
        path_metrics = (
            Path(**path_metrics) if path_metrics else Path(url=url.url, redirects=1)
        )
        r = await path_metrics_collection.find_one_and_update(
            {"url": path_metrics.url},
            {
                "$set": path_metrics.dict(exclude={"redirects"}),
                "$inc": {"redirects": 1},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        host_metrics = (
            Host(**host_metrics)
            if host_metrics
            else Host(paths_ids=[r["_id"]], host=url.url.host, total_redirects=1)
        )

        await host_metrics_collection.find_one_and_update(
            {"host": host_metrics.host}, {"$set": host_metrics.dict()}, upsert=True
        )
