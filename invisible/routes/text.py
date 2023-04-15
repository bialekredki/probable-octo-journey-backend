from fastapi import APIRouter
from fastapi_cbv.view import view
from fastapi_cbv.endpoint import endpoint

router = APIRouter(prefix="/text", tags=["Texts"])


@view(router)
class TextView:
    async def post(self):
        pass

    async def get(self):
        pass

    async def patch(self):
        pass
