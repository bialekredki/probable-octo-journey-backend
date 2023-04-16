from datetime import datetime, timedelta

import orjson
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi_cbv.endpoint import endpoint
from fastapi_cbv.view import view
from pymongo.results import InsertOneResult

from invisible.app import TypedApp, TypedRequest
from invisible.models import URL
from invisible.schemas import CreateTinyURL
from invisible.types import TinyURL
from invisible.messaging import send_message

router = APIRouter(prefix="/url", tags=["URLs"])


async def update_cache(
    app: TypedApp, tiny_url: str, url: str, max_reads: int | None = None
):
    await app.redis.set(
        tiny_url,
        orjson.dumps([url, max_reads]),
        ex=timedelta(minutes=app.config.cache_ttl),
    )


async def remove_from_cache(app: TypedApp, tiny_url: str):
    await app.redis.delete(tiny_url)


@view(router)
class URLShortenerView:
    async def post(
        self,
        request: TypedRequest,
        background_tasks: BackgroundTasks,
        data: CreateTinyURL,
    ):
        url = URL(**data.dict())
        result: InsertOneResult = await request.app.database["tinyurl"].insert_one(
            url.dict()
        )
        background_tasks.add_task(
            update_cache, request.app, url.tiny_url, url.url, url.max_redirects
        )
        url = await request.app.database["tinyurl"].find_one(
            {"_id": result.inserted_id}
        )
        url = URL(**url)
        background_tasks.add_task(send_message, request.app.producer, "create", url)
        return url

    @endpoint(methods=["GET"], path="{tiny_url}", response_class=RedirectResponse)
    async def get(
        self,
        request: TypedRequest,
        background_tasks: BackgroundTasks,
        tiny_url: TinyURL,
    ):
        url = await request.app.redis.get(tiny_url)
        if url:
            url, max_redirects = orjson.loads(url)
            if max_redirects:
                if max_redirects == 1:
                    background_tasks.add_task(remove_from_cache, request.app, tiny_url)
                else:
                    background_tasks.add_task(
                        update_cache, request.app, tiny_url, url, max_redirects - 1
                    )
            background_tasks.add_task(
                send_message,
                request.app.producer,
                "read",
                URL(url=url, max_redirects=max_redirects, tiny_url=tiny_url),
            )
            return RedirectResponse(url=url)
        url = await request.app.database["tinyurl"].find_one({"tiny_url": tiny_url})
        try:
            url = URL(**url)
            if url.max_redirects == 0 or url.is_expired:
                raise ValueError()
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This tiny URL doesn't exist.",
            ) from exc
        background_tasks.add_task(
            update_cache, request.app, url.tiny_url, url.url, url.max_redirects
        )
        background_tasks.add_task(send_message, request.app.producer, "read", url)
        return RedirectResponse(url=url.url)

    async def patch(self):
        pass

    async def delete(self):
        pass

    @endpoint(methods=["GET"], path="{tiny_url}/details", response_model=URL)
    async def view(
        self, request: TypedRequest, background_task: BackgroundTasks, tiny_url: TinyURL
    ):
        url = await request.app.database["tinyurl"].find_one({"tiny_url": tiny_url})
        if url is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This tiny URL doesn't exist.",
            )
        url = URL(**url)
        if not url.is_expired:
            background_task.add_task(
                update_cache, request.app, url.tiny_url, url.url, url.max_redirects
            )
        return url
