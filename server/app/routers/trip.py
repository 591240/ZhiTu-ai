from fastapi import APIRouter, Depends, Query

from app.schemas import TripSaveReq, ok, fail
from app.deps import get_current_user
from app.services.trip_service import trip_service

router = APIRouter(prefix="/api/trip", tags=["trip"])


@router.get("/list")
async def list_trip(status: str = None, user=Depends(get_current_user)):
    return ok({"list": await trip_service.list(user["user_id"], status)})


@router.get("/detail")
async def detail(id: int = Query(...), user=Depends(get_current_user)):
    t = await trip_service.detail(id, user["user_id"])
    if not t:
        return fail("行程不存在")
    return ok({"trip": t})


@router.post("/save")
async def save(req: TripSaveReq, user=Depends(get_current_user)):
    tid = await trip_service.save(user["user_id"], req.trip)
    return ok({"id": tid})


@router.post("/delete")
async def delete(body: dict, user=Depends(get_current_user)):
    tid = body.get("id")
    if tid:
        await trip_service.delete(int(tid), user["user_id"])
    return ok({})
