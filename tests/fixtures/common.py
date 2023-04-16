import asyncio

import pytest
from httpx import AsyncClient
from mongomock_motor import AsyncMongoMockClient, AsyncMongoMockDatabase

from invisible import initialize_application
from invisible.app import TypedApp
from invisible.models import URL


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", name="app")
async def fixture_app(mock_redis):
    yield initialize_application()


@pytest.fixture
async def client(app: TypedApp):
    app.db_client = AsyncMongoMockClient()
    app.database = app.db_client["test"]
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.redis.clean()


@pytest.fixture
def test_url():
    return "http://test.xyz"


@pytest.fixture
def test_url_model(test_url: str):
    return URL(url=test_url)
