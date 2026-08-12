from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user
from app.schemas import ok
from app.services.ota_service import ota_service

router = APIRouter(prefix="/api/ota", tags=["ota"])


@router.get("/channels")
async def channels(
    category: str = Query("ticket", description="品类：ticket / food / hotel"),
    query: str = Query("", description="搜索词，如景点名 / 城市名"),
    user=Depends(get_current_user),
):
    """返回该品类的购票 / 团购 / 订房渠道列表（含搜索深链）。离线可用，无需企业资质。"""
    return ok(ota_service.list_channels(category, query))


@router.get("/price")
async def price(
    category: str = Query(..., description="品类：ticket / food / hotel"),
    query: str = Query(..., description="搜索词，如景点名 / 城市名"),
    channel: str = Query(None, description="指定渠道 key，可选"),
    user=Depends(get_current_user),
):
    """查询实时价格（预留）。当前返回 available=False，引导走推荐渠道+跳转；
    接入 OTA 开放平台后改为返回真实比价。"""
    return ok(ota_service.query_price(category, query, channel))
