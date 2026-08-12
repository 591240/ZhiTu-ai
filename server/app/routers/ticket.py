from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user
from app.schemas import ok, fail
from app.services.ticket_service import ticket_service

router = APIRouter(prefix="/api/ticket", tags=["ticket"])


@router.get("/search")
async def search(
    date: str = Query(..., description="出发日期，格式 YYYY-MM-DD"),
    from_station: str = Query(..., description="出发城市或车站名，如 北京"),
    to_station: str = Query(..., description="到达城市或车站名，如 杭州"),
    train_type: str = Query(None, description="车次类型筛选，如 G/D/K，可选"),
    user=Depends(get_current_user),
):
    """查询 12306 真实余票/车次（经 12306-mcp）。失败自动降级估算。"""
    try:
        data = await ticket_service.search(date, from_station, to_station, train_type)
    except Exception as e:
        return fail(str(e))
    return ok(data)
