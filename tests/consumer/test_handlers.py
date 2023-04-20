from datetime import datetime, timedelta

import pytest
from mongomock_motor import AsyncMongoMockClient, AsyncMongoMockCollection
from pydantic import BaseModel

from invisible.consumers.handlers import BaseHandler, HandleLastVisitTime
from invisible.consumers.utils import ParsedRecord
from invisible.messaging import send_message
from invisible.models import URL
from tests.fixtures.producer import MockKafkaProducer


async def emit_message(
    data: BaseModel, handler: BaseHandler, dt: datetime | None = None
):
    dt = dt or datetime.now()
    timestamp = dt.timestamp() * 1000
    producer = MockKafkaProducer()
    await send_message(producer, "read", data)
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
def tinyurl_collection():
    return AsyncMongoMockClient()["test"]["tinyurl"]


@pytest.fixture
def handler_last_visit_time(tinyurl_collection):
    handler = HandleLastVisitTime()
    handler.services = {"tinyurl_collection": tinyurl_collection}
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
        test_url_model, handler_last_visit_time, datetime.now() - timedelta(minutes=10)
    )
    res = await tinyurl_collection.find_one({"tiny_url": test_url_model.tiny_url})
    assert (
        res["max_redirects"] == max_redirects
        if not max_redirects
        else max_redirects - 1
    )
