from unittest.mock import patch

import pytest


class MockKafkaProducer:
    def __init__(self) -> None:
        pass

    async def send(self, *args, **kwargs):
        pass

    def __call__(self):
        return self

    async def start(self):
        pass


@pytest.fixture(scope="session")
def mocked_producer():
    with patch("aiokafka.AIOKafkaProducer", MockKafkaProducer) as mocked:
        yield mocked
