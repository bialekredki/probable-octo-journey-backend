import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from mongomock_motor import AsyncMongoMockClient, AsyncMongoMockCollection
from pydantic import BaseModel

from app.consumers.handlers import (
    BaseHandler,
    HandleAnalytics,
    HandleLastVisitTime,
    HandleMetrics,
)
from app.consumers.utils import ParsedRecord
from app.messaging import send_message
from app.models import URL
from app.models.metrics import Host, Path
from tests.fixtures.producer import MockKafkaProducer


ANALYTICS_COLUMNS = (
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
)


async def emit_message(
    data: BaseModel,
    handler: BaseHandler,
    action: str,
    dt: datetime | None = None,
    *,
    additional_data: dict[str, Any] | None = None
):
    dt = dt or datetime.now()
    timestamp = dt.timestamp() * 1000
    producer = MockKafkaProducer()
    await send_message(producer, action, data, additional_data=additional_data)
    topic, value = producer.get(decode_value=True)
    record = ParsedRecord(
        topic=topic,
        parition=0,
        offset=0,
        timestamp=timestamp,
        value=value,
        key=None,
        timestamp_type=0,
    )
    await handler(record)
    return record


def compare_datetimes(_dt1: datetime, _dt2: datetime, epsilon_seconds: int):
    return -epsilon_seconds <= (_dt1 - _dt2).total_seconds() < epsilon_seconds


def kafka_timestamp_to_datetime(timestamp: int):
    return datetime.fromtimestamp(timestamp / 1000)


@pytest.fixture
def mongo_database():
    return AsyncMongoMockClient()["test"]


@pytest.fixture
def tinyurl_collection(mongo_database):
    return mongo_database["tinyurl"]


@pytest.fixture
def host_metrics_collection(mongo_database):
    return mongo_database["host_metrics"]


@pytest.fixture
def path_metrics_collection(mongo_database):
    return mongo_database["path_metrics"]


@pytest.fixture
def handler_last_visit_time(tinyurl_collection):
    handler = HandleLastVisitTime()
    handler.services = {"tinyurl_collection": tinyurl_collection}
    return handler


@pytest.fixture
def handler_metrics(path_metrics_collection, host_metrics_collection):
    handler = HandleMetrics()
    handler.services = {
        "host_metrics_collection": host_metrics_collection,
        "path_metrics_collection": path_metrics_collection,
    }
    return handler


@pytest.fixture
def handler_analytics(ip_reader, mocked_clickhouse):
    handler = HandleAnalytics()
    handler.services = {"ip_reader": ip_reader, "clickhouse_client": mocked_clickhouse}
    return handler


@pytest.mark.parametrize(
    "timediff_between_emission",
    (
        pytest.param(
            timedelta(minutes=0), id="Both message and last visit were done now."
        ),
        pytest.param(
            timedelta(minutes=-3), id="Last visit was done before message was sent."
        ),
        pytest.param(
            timedelta(minutes=3), id="Last visit was done after message was sent."
        ),
    ),
)
async def test_handle_last_visit_time__message_older_than_last_visit(
    test_url_model: URL,
    tinyurl_collection,
    handler_last_visit_time,
    timediff_between_emission,
):
    emission_time = datetime.now() + timediff_between_emission
    test_url_model.last_visit_time = datetime.now()

    await tinyurl_collection.insert_one(test_url_model.dict())
    await emit_message(
        test_url_model,
        handler_last_visit_time,
        "read",
        emission_time,
    )
    res = await tinyurl_collection.find_one({"tiny_url": test_url_model.tiny_url})

    assert compare_datetimes(
        res["last_visit_time"], max(emission_time, test_url_model.last_visit_time), 60
    )


@pytest.mark.parametrize(
    "max_redirects",
    (
        pytest.param(0, id="Zero redirects left."),
        pytest.param(2, id="Positive number of redirects left."),
        pytest.param(None, id="No number of redirects specified."),
    ),
)
async def test_handle_last_visit_time__max_redirects(
    test_url_model: URL, tinyurl_collection, handler_last_visit_time, max_redirects
):
    test_url_model.max_redirects = max_redirects
    await tinyurl_collection.insert_one(test_url_model.dict())
    await emit_message(
        test_url_model,
        handler_last_visit_time,
        "read",
        datetime.now() - timedelta(minutes=10),
    )
    res = await tinyurl_collection.find_one({"tiny_url": test_url_model.tiny_url})
    assert (
        res["max_redirects"] == max_redirects
        if not max_redirects
        else max_redirects - 1
    )


async def test_metrics_handler__first_time_creation(
    handler_metrics,
    host_metrics_collection,
    path_metrics_collection,
    test_url_model: URL,
):
    await emit_message(test_url_model, handler_metrics, "create")
    host_metrics, path_metrics = await asyncio.gather(
        *(host_metrics_collection.find_one({}), path_metrics_collection.find_one({}))
    )
    host_metrics, path_metrics = Host(**host_metrics), Path(**path_metrics)

    assert host_metrics.host == test_url_model.url.host
    assert path_metrics.url == test_url_model.url
    assert path_metrics.id in host_metrics.paths_ids
    assert all(
        redirect == 0
        for redirect in (host_metrics.total_redirects, path_metrics.redirects)
    )
    assert all(
        tiny_urls == 1
        for tiny_urls in (host_metrics.total_tiny_urls, path_metrics.tiny_urls)
    )


async def test_metrics_handler__metric_created_for_another_path(
    handler_metrics,
    host_metrics_collection,
    path_metrics_collection,
    test_url_model: URL,
):
    another_path_metrics = Path(url=test_url_model.url + "/additional")
    original_host_metrics = Host(
        host=test_url_model.url.host,
        total_tiny_urls=1,
        paths_ids=[another_path_metrics.id],
    )

    await asyncio.gather(
        *(
            host_metrics_collection.insert_one(original_host_metrics.dict()),
            path_metrics_collection.insert_one(another_path_metrics.dict()),
        )
    )

    await emit_message(test_url_model, handler_metrics, "create")

    host_metrics, path_metrics = await asyncio.gather(
        *(
            host_metrics_collection.find_one({}),
            path_metrics_collection.find_one({"url": test_url_model.url}),
        )
    )
    host_metrics, path_metrics = Host(**host_metrics), Path(**path_metrics)

    assert host_metrics.host == test_url_model.url.host
    assert path_metrics.url == test_url_model.url
    assert len(host_metrics.paths_ids) == 2
    assert path_metrics.id in host_metrics.paths_ids

    assert host_metrics.total_tiny_urls == 2
    assert host_metrics.total_redirects == 0

    assert path_metrics.tiny_urls == 1
    assert path_metrics.redirects == 0


async def test_metrics_handler__update_metrics(
    handler_metrics,
    host_metrics_collection,
    path_metrics_collection,
    test_url_model: URL,
):
    path_metrics = Path(url=test_url_model.url)
    host_metrics = Host(
        host=test_url_model.url.host,
        total_tiny_urls=1,
        paths_ids=[path_metrics.id],
    )

    await asyncio.gather(
        *(
            host_metrics_collection.insert_one(host_metrics.dict()),
            path_metrics_collection.insert_one(path_metrics.dict()),
        )
    )

    await emit_message(test_url_model, handler_metrics, "read")

    host_metrics, path_metrics = await asyncio.gather(
        *(
            host_metrics_collection.find_one({}),
            path_metrics_collection.find_one({"url": test_url_model.url}),
        )
    )
    host_metrics, path_metrics = Host(**host_metrics), Path(**path_metrics)

    assert host_metrics.host == test_url_model.url.host
    assert path_metrics.url == test_url_model.url
    assert len(host_metrics.paths_ids) == 2
    assert path_metrics.id in host_metrics.paths_ids

    assert host_metrics.total_tiny_urls == 1
    assert host_metrics.total_redirects == 1

    assert path_metrics.tiny_urls == 1
    assert path_metrics.redirects == 1


@pytest.mark.parametrize(
    ("ip_address", "expected_location"),
    (
        pytest.param(None, "Unknown", id="No IP Address given in the record."),
        pytest.param("207.23.240.87", "CA", id="A Canadian IP Address."),
        pytest.param("207.226.217.15", "HK", id="A Hong Kong IP Address."),
        pytest.param("192.168.1.15", "Unknown", id="A private IP address."),
    ),
)
async def test_analytics_handler__ip_address(
    test_url_model: URL,
    handler_analytics,
    mocked_clickhouse: MagicMock,
    ip_address: str,
    expected_location: str,
):
    record = await emit_message(
        test_url_model,
        handler_analytics,
        "read",
        additional_data={"ip_address": ip_address},
    )

    mocked_clickhouse.insert.assert_called_once()
    mocked_clickhouse.insert.assert_called_with(
        "analytics",
        [
            (
                test_url_model.url.host,
                str(test_url_model.url),
                test_url_model.tiny_url,
                kafka_timestamp_to_datetime(record.timestamp),
                ip_address,
                expected_location,
                "Unknown",
                "Unknown",
                "Unknown",
                False,
                False,
            )
        ],
        ANALYTICS_COLUMNS,
    )
