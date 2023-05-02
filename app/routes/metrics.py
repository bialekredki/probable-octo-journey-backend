from fastapi import APIRouter, Query
from pydantic import constr

from app.app import TypedRequest
from app.models.metrics import Host

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("")
async def get_metrics(
    request: TypedRequest,
    query: constr(strip_whitespace=True, strict=True, min_length=1)
    | None = Query(None, alias="q"),
):
    db_query = {"$text": {"$search": query}} if query else None
    r = (
        await request.app.database["host_metrics"]
        .find(db_query, limit=50)
        .to_list(length=50)
    )
    return [Host(**metrics) for metrics in r]
