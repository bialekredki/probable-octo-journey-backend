from typing import Iterable

from fastapi import APIRouter, Depends
from fastapi_cbv import endpoint, view

from app.app import TypedRequest
from app.schemas.analytics import AnalyticsStatsItem, AnalyticsStatsRequest

router = APIRouter(prefix="/analytics", tags=["Metrics", "Analytics"])


@view(router, path="/tiny_url/{tiny_url_id}")
class TinyUrlAnalyticsView:
    @endpoint(
        methods=["GET"],
        name="TinyURL stats",
        path="/stats",
        response_model=list[AnalyticsStatsItem],
    )
    async def stats(self, tiny_url_id: str, request: TypedRequest, params: AnalyticsStatsRequest = Depends()):
        params = params.dict()
        params["tiny_url_id"] = tiny_url_id
        r = request.app.clickhouse_client.query(
            """
                SELECT count(*) as visits, toDate(timestamp) as day, uniqCombined((device, operating_system, browser, ip_address)) as unique_visits 
                FROM analytics 
                WHERE tiny_url = {tiny_url_id:String} 
                    AND day >= {start_date: DateTime}
                    AND day <= {end_date: DateTime}
                GROUP BY day
                ORDER BY day
            """,
            parameters=params,
        )
        return list(r.named_results())

