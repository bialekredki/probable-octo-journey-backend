from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar
from unittest.mock import patch

import pytest

T = TypeVar("T")


@dataclass
class Expirable(Generic[T]):
    data: T
    ttl: int | None
    created_at: datetime = datetime.now()
    fetch_times: int = 0

    @property
    def is_expired(self):
        return (
            self.ttl and timedelta(seconds=self.ttl) <= datetime.now() - self.created_at
        )


class AioRedisMock:
    def __init__(self, *args, **kwargs) -> None:
        self.store: dict[Any, Expirable] = {}

    async def set(
        self,
        key: Any,
        value: Any,
        ex: timedelta | None = None,
        __created_at: datetime | None = None,
    ):
        self.store[key] = Expirable(data=value, ttl=ex.seconds if ex else ex)

    async def get(self, key):
        res = self.store.get(key)
        if res and res.is_expired:
            del self.store[key]
            res = None
        elif res:
            res.fetch_times += 1
        return bytes(res.data, encoding="utf-8") if res else None

    def clean(self):
        self.store = {}


@pytest.fixture(scope="session")
async def mock_redis():
    with patch("aioredis.from_url", AioRedisMock) as mocked:
        yield mocked
