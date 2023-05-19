import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from clickhouse_connect.driver import Client
from geoip2.database import Reader
from geoip2.errors import AddressNotFoundError
from user_agents import parse

from motor.core import Collection
from pymongo.collection import ReturnDocument

from app.consumers.utils import RecordT
from app.models import URL
from app.models.metrics import Host, Path


PRIVATE_IP_ADDRESS = "192.168.1.1"


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
            update_fields = {
                "$set": {"last_visit_time": record_datetime},
            }
            if url.max_redirects is not None and url.max_redirects >= 1:
                update_fields["$inc"] = {"max_redirects": -1}
            await tiny_url_collection.update_one({"_id": url.id}, update_fields)


class HandleAnalytics(BaseHandler):
    async def __call__(self, record: RecordT) -> Any:
        client: Client = self.services["clickhouse_client"]
        ip_reader: Reader = self.services["ip_reader"]

        url = URL(**record.value)
        try:
            location = ip_reader.country(
                record.value.get("ip_address", PRIVATE_IP_ADDRESS) or PRIVATE_IP_ADDRESS
            ).country.iso_code
        except AddressNotFoundError:
            location = "Unknown"
        if "user_agent" in record.value and record.value.get("user_agent"):
            user_agent = parse(record.value["user_agent"])

        try:
            device = user_agent.device.family
            browser = f"{user_agent.os.family} {user_agent.os.version_string}"
            operating_system = (
                f"{user_agent.browser.family} {user_agent.browser.version_string}"
            )
            is_mobile = user_agent.is_mobile
            is_bot = user_agent.is_bot
        except UnboundLocalError:
            device, browser, operating_system = ("Unknown",) * 3
            is_mobile, is_bot = (False,) * 2
        client.insert(
            "analytics",
            [
                (
                    url.url.host,
                    str(url.url),
                    url.tiny_url,
                    datetime.fromtimestamp(record.timestamp / 1000),
                    record.value.get("ip_address"),
                    location,
                    device,
                    operating_system,
                    browser,
                    is_mobile,
                    is_bot,
                )
            ],
            (
                "host",
                "path",
                "tiny_url",
                "timestamp",
                "ip_address",
                "location",
                "device",
                "operating_system",
                "browser",
                "is_mobile",
                "is_bot",
            ),
        )


class HandleMetrics(BaseHandler):
    async def __call__(self, record: RecordT) -> Any:
        # TODO: Refactor this handler
        host_metrics_collection: Collection = self.services["host_metrics_collection"]
        path_metrics_collection: Collection = self.services["path_metrics_collection"]

        url = URL(**record.value)
        host_url = url.url.host.replace("www.", "")

        host_metrics, path_metrics = await asyncio.gather(
            *[
                host_metrics_collection.find_one({"host": host_url}),
                path_metrics_collection.find_one({"url": url.url}),
            ]
        )
        redirects_number = 1 if record.topic.endswith("read") else 0
        incremented_fields = (
            {"redirects"} if record.topic.endswith("read") else {"tiny_urls"}
        )
        tiny_urls = 0 if record.topic.endswith("read") else 1
        path_metrics = (
            Path(**path_metrics)
            if path_metrics
            else Path(url=url.url, redirects=redirects_number, tiny_urls=tiny_urls)
        )
        fields_to_set = path_metrics.dict(
            exclude=incremented_fields | {"id", "path"},
        )
        fields_to_set.update({"search": path_metrics.url})
        r = await path_metrics_collection.find_one_and_update(
            {"url": path_metrics.url},
            {
                "$set": fields_to_set,
                "$inc": {inc_field: 1 for inc_field in incremented_fields},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        host_metrics = (
            Host(**host_metrics)
            if host_metrics
            else Host(
                paths_ids=[],
                host=host_url,
                total_redirects=redirects_number,
                tiny_urls=tiny_urls,
            )
        )
        host_metrics.paths_ids.append(r["_id"])
        incremented_fields = (
            {"total_redirects"}
            if record.topic.endswith("read")
            else {"total_tiny_urls"}
        )
        fields_to_set = host_metrics.dict(
            exclude=incremented_fields | {"id", "path"},
        )
        fields_to_set.update({"search": host_metrics.host})
        await host_metrics_collection.find_one_and_update(
            {"host": host_metrics.host},
            {
                "$set": fields_to_set,
                "$inc": {inc_field: 1 for inc_field in incremented_fields},
            },
            upsert=True,
        )
