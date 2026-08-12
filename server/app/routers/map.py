from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user
from app.schemas import ok, fail
from app.services.geocode_service import geocode_service

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("/geocode")
async def geocode(
    name: str = Query(..., description="地点/车站名，如 杭州东站"),
    city: str = Query("", description="所属城市，如 杭州（可消除同名地点歧义）"),
    user=Depends(get_current_user),
):
    """地名/车站 → 经纬度（腾讯位置服务优先，降级高德 MCP / REST / 内置表）。"""
    try:
        data = await geocode_service.geocode(name, city)
    except Exception as e:
        return fail(str(e))
    if not data:
        return fail(f"未找到「{name}」的坐标")
    return ok(data)


@router.get("/geocode-batch")
async def geocode_batch(
    names: str = Query(..., description="逗号分隔的多个地点名，如 西湖,灵隐寺,河坊街"),
    city: str = Query("", description="所属城市，如 杭州（可消除同名地点歧义）"),
    user=Depends(get_current_user),
):
    """批量地理编码（景点距离计算用），返回与输入顺序一致的结果列表。"""
    try:
        name_list = [n.strip() for n in names.split(",") if n.strip()]
        results = await geocode_service.geocode_batch(name_list, city)
    except Exception as e:
        return fail(str(e))
    return ok({"results": results})
