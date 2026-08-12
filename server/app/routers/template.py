from fastapi import APIRouter, Depends, Query

from app.schemas import ok, fail
from app.deps import get_current_user
from app.services.template_service import template_service

router = APIRouter(prefix="/api/template", tags=["template"])


@router.get("/hot")
async def hot(user=Depends(get_current_user)):
    return ok({"list": await template_service.hot()})


@router.get("/detail")
async def detail(id: int = Query(...), user=Depends(get_current_user)):
    t = await template_service.detail(id)
    if not t:
        return fail("模板不存在")
    return ok({"template": t})


@router.post("/use")
async def use(body: dict, user=Depends(get_current_user)):
    content = await template_service.use(int(body.get("id")))
    if not content:
        return fail("模板不存在")
    return ok({"content": content})


@router.post("/publish")
async def publish(body: dict, user=Depends(get_current_user)):
    ok_pub = await template_service.publish(user["user_id"], int(body.get("id")))
    if not ok_pub:
        return fail("模板不存在")
    return ok({"published": True})


@router.get("/published")
async def published(user=Depends(get_current_user)):
    return ok({"list": await template_service.published(user["user_id"])})
