from fastapi import APIRouter, Depends

from app.schemas import ok, fail
from app.deps import get_current_user
from app.services.distribution_service import distribution_service

router = APIRouter(prefix="/api/distribution", tags=["distribution"])


@router.post("/bind")
async def bind(body: dict, user=Depends(get_current_user)):
    code = body.get("invite_code", "")
    res = await distribution_service.bind(code, user["user_id"])
    if not res.get("ok"):
        return fail(res.get("message", "绑定失败"))
    return ok(res)


@router.get("/my")
async def my(user=Depends(get_current_user)):
    data = await distribution_service.my(user["user_id"])
    return ok(data)
