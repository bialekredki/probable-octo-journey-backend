from fastapi import APIRouter
from fastapi_cbv.endpoint import endpoint
from fastapi_cbv.view import view

router = APIRouter(prefix="/file", tags=["Files"])


@view(router)
class FileView:
    async def post(self):
        pass

    async def get(self):
        pass

    async def patch(self):
        pass
