import orjson
from fastapi import status
from httpx import AsyncClient

from app.app import TypedApp
from app.models import URL
from app.schemas import CreateTinyURL


async def test_cache_is_refreshed_after_insert(
    client: AsyncClient, app: TypedApp, test_url: str
):
    response = await client.post("/url/", json=CreateTinyURL(url=test_url).dict())
    url = URL(**response.json())
    assert response.status_code == status.HTTP_201_CREATED
    data = orjson.loads((await app.redis.get(url.tiny_url)))
    assert data[0] == url.url


async def test_url_is_fetched_from_cached_if_present(
    client: AsyncClient, app: TypedApp, test_url: str, faker
):
    tiny_url = faker.pystr(min_chars=16, max_chars=16)
    await app.redis.set(tiny_url, orjson.dumps((test_url, None)))
    response = await client.get(f"/url/{tiny_url}", follow_redirects=False)

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert app.redis.store[tiny_url].fetch_times == 1


async def test_url_is_cached_after_redirect(
    client: AsyncClient, app: TypedApp, test_url: str
):
    url = URL(url=test_url)
    await app.database["tinyurl"].insert_one(url.dict())
    response = await client.get(f"/url/{url.tiny_url}", follow_redirects=False)

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert app.redis.store[url.tiny_url].fetch_times == 0
    assert len(app.producer.queue) == 1
    assert app.producer.get()[0] == "URL.read"


async def test_cache_is_refreshed_after_details(
    client: AsyncClient, app: TypedApp, test_url: str
):
    url = URL(url=test_url)
    await app.redis.set(url.tiny_url, url.url)
    await app.database["tinyurl"].insert_one(url.dict())

    response = await client.get(f"/url/{url.tiny_url}/details")

    assert response.status_code == status.HTTP_200_OK
    data = orjson.loads((await app.redis.get(url.tiny_url)))
    assert data[0] == url.url
