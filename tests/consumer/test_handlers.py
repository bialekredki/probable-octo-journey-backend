from datetime import datetime, timedelta
import asyncio
import pytest
from mongomock_motor import AsyncMongoMockClient, AsyncMongoMockCollection
from pydantic import BaseModel

from invisible.consumers.handlers import BaseHandler, HandleLastVisitTime, HandleMetrics
from invisible.consumers.utils import ParsedRecord
from invisible.messaging import send_message
from invisible.models import URL
from invisible.models.metrics import Path, Host
from tests.fixtures.producer import MockKafkaProducer


async def emit_message(
    data: BaseModel, handler: BaseHandler, action: str, dt: datetime | None = None
):
    dt = dt or datetime.now()
    timestamp = dt.timestamp() * 1000
    producer = MockKafkaProducer()
    await send_message(producer, action, data)
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
