from fastapi import APIRouter

from app.schemas import ok

router = APIRouter(prefix="/api/service", tags=["service"])

SERVICES = [
    {"key": "map", "name": "导航", "app_id": "", "path": ""},
    {"key": "car", "name": "打车", "app_id": "", "path": ""},
    {"key": "hotel", "name": "酒店", "app_id": "", "path": ""},
    {"key": "food", "name": "美食", "app_id": "", "path": ""},
    {"key": "flight", "name": "机票高铁", "app_id": "", "path": ""},
    {"key": "ticket", "name": "景区门票", "app_id": "", "path": ""},
    {"key": "movie", "name": "电影票", "app_id": "", "path": ""},
    {"key": "takeout", "name": "外卖", "app_id": "", "path": ""},
]


@router.get("/list")
async def list_services():
    return ok({"list": SERVICES})
