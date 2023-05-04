from fastapi import APIRouter
from fastapi_cbv import endpoint, view

from app.app import TypedRequest
from typing import Iterable
from app.schemas.analytics import AnalyticsStatsItem

router = APIRouter(prefix="/analytics", tags=["Metrics", "Analytics"])


@view(router, path="/tiny_url/{tiny_url_id}")
class TinyUrlAnalyticsView:
    @endpoint(
        methods=["GET"],
        name="stats",
        path="/stats",
        response_model=AnalyticsStatsItem,
    )
    async def stats(self, tiny_url_id: str, request: TypedRequest):
        r = request.app.clickhouse_client.query(
            """
                SELECT count(*) as visits, toDate(timestamp) as day, uniqCombined((device, operating_system, browser, ip_address)) as unique_visits 
                FROM analytics 
                WHERE tiny_url = {tiny_url_id:String} 
                GROUP BY day
                ORDER BY day
            """,
            parameters={"tiny_url_id": tiny_url_id},
        )
        return list(r.named_results())
