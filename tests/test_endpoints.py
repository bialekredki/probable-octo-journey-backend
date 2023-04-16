import pytest
from fastapi import status
from httpx import AsyncClient

from invisible.app import TypedApp
from invisible.models import URL
from invisible.schemas import CreateTinyURL


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

    assert response.status_code == status.HTTP_200_OK
    assert res is not None

    database_url = URL(**res)

    assert response_url.url == database_url.url == test_url
    assert response_url.max_redirects == database_url.max_redirects == max_redirects
    assert response_url.time_to_live == database_url.time_to_live == ttl


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
