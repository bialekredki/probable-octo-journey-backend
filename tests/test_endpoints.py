import orjson
import pytest
from fastapi import status
from httpx import AsyncClient

from app.app import TypedApp
from app.models import URL
from app.messaging import _default_objectid
from app.schemas import CreateTinyURL


@pytest.mark.parametrize(
    "ttl, max_redirects",
    (
        pytest.param(None, None, id="No limit."),
        pytest.param(60, 3, id="With limiting."),
        pytest.param(None, 5, id="Limit only TTL."),
        pytest.param(120, None, id="Limit only max_redirects."),
    ),
)
async def test_create_endpoint(
    client: AsyncClient,
    app: TypedApp,
    test_url: URL,
    ttl: int | None,
    max_redirects: int | None,
):
    response = await client.post(
        f"/url/",
        json=CreateTinyURL(url=test_url, ttl=ttl, max_redirects=max_redirects).dict(
            by_alias=True
        ),
    )
    response_url = URL(**response.json())
    res = await app.database["tinyurl"].find_one({"_id": response_url.id})

    assert response.status_code == status.HTTP_201_CREATED
    assert res is not None

    database_url = URL(**res)

    assert response_url.url == database_url.url == test_url
    assert response_url.max_redirects == database_url.max_redirects == max_redirects
    assert response_url.time_to_live == database_url.time_to_live == ttl

    assert len(app.producer.queue) == 1
    assert app.producer.get() == (
        "URL.create",
        orjson.dumps(database_url.dict(), default=_default_objectid),
    )


@pytest.mark.parametrize(
    "ttl, max_redirects",
    (
        pytest.param(None, None, id="No limit."),
        pytest.param(60, 3, id="With limiting."),
        pytest.param(None, 5, id="Limit only TTL."),
        pytest.param(120, None, id="Limit only max_redirects."),
    ),
)
async def test_redirect_endpoint(
    client: AsyncClient,
    app: TypedApp,
    test_url_model: URL,
    ttl: int | None,
    max_redirects: int | None,
):
    test_url_model.time_to_live = ttl
    test_url_model.max_redirects = max_redirects
    res = await app.database["tinyurl"].insert_one(test_url_model.dict())
    response = await client.get(
        f"/url/{test_url_model.tiny_url}", follow_redirects=False
    )

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert "location" in response.headers
    assert response.headers["location"] == test_url_model.url

    assert len(app.producer.queue) == 1


@pytest.mark.parametrize("size", (2**_ for _ in range(12)))
@pytest.mark.timeout(5)
async def test_bulk_create(client: AsyncClient, app: TypedApp, size: int, faker):
    response = await client.post(
        "/url/bulk", json=[CreateTinyURL(url=faker.url()).dict() for _ in range(size)]
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert len(app.producer.queue) == size
    data = response.json()
    r = app.database["tinyurl"].find(
        {"tiny_url": {"$in": [d["tiny_url"] for d in data]}}, ["tiny_url", "url"]
    )
    r = await r.to_list(length=100)
    assert len(r) == len(data)
