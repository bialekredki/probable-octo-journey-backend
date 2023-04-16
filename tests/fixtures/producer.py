from collections import deque
from typing import Any
from unittest.mock import patch

import orjson
import pytest


class MockKafkaProducer:
    def __init__(self) -> None:
        self.queue: deque[tuple[Any, Any]] = deque()

    async def send(self, topic, value):
        self.queue.append((topic, value))

    def get(self, *, decode_value: bool = False):
        topic, value = self.queue.popleft()
        if decode_value:
            value = orjson.loads(value)
        return topic, value

    def __call__(self):
        return self

    async def start(self):
        pass

    def clean(self):
        self.queue.clear()


@pytest.fixture(scope="session")
def mocked_producer():
    with patch("aiokafka.AIOKafkaProducer", MockKafkaProducer) as mocked:
        yield mocked
