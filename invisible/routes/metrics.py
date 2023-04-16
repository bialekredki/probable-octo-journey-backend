from fastapi import APIRouter, Query
from pydantic import constr

from invisible.app import TypedRequest
from invisible.models.metrics import Host

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("")
async def get_metrics(
    request: TypedRequest,
    query: constr(strip_whitespace=True, strict=True, min_length=1)
    | None = Query(None, alias="q"),
):
    db_query = {"$text": {"$search": query}} if query else None
    r = await request.app.database["host_metrics"].find(db_query).to_list(length=10000)
    print(r)
    return [Host(**metrics) for metrics in r]
