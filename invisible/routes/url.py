from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi_cbv.endpoint import endpoint
from fastapi_cbv.view import view
from pymongo.results import InsertOneResult

from invisible.app import TypedRequest
from invisible.models import URL
from invisible.schemas import CreateTinyURL
from invisible.types import TinyURL

router = APIRouter(prefix="/url", tags=["URLs"])


@view(router)
class URLShortenerView:
    async def post(self, request: TypedRequest, data: CreateTinyURL):
        url = URL(**data.dict())
        x: InsertOneResult = await request.app.database["tinyurl"].insert_one(url.dict())
        url = await request.app.database["tinyurl"].find_one({"_id": x.inserted_id})
        return URL(**url)

    @endpoint(methods=["GET"], path="{tiny_url}", response_class=RedirectResponse)
    async def get(self, request: TypedRequest, tiny_url: TinyURL):
        url = await request.app.database["tinyurl"].find_one({"tiny_url": tiny_url})
        try:
            url = URL(**url)
            if url.max_redirects == 0 or (url.time_to_live is not None and timedelta(hours=url.time_to_live) <= datetime.now() - url.creation_time):
                raise ValueError()
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This tiny URL doesn't exist.")
            
        # TODO: Send metrics message by Kafka
        return RedirectResponse(url=url["url"])

    async def patch(self):
        pass

    async def delete(self):
        pass

    @endpoint(methods=["GET"], path="{tiny_url}/details", response_model=URL)
    async def view(self, request: TypedRequest, tiny_url: TinyURL):
        url = await request.app.database["tinyurl"].find_one({"tiny_url": tiny_url})
        if url is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This tiny URL doesn't exist.")
        return url
