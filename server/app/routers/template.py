from fastapi import APIRouter, Depends, Query

from app.schemas import IdReq, ok, fail
from app.deps import get_current_user
from app.services.template_service import template_service
from app.utils.wechat import check_text_security, collect_text

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
async def use(req: IdReq, user=Depends(get_current_user)):
    content = await template_service.use(req.id)
    if not content:
        return fail("模板不存在")
    return ok({"content": content})


@router.post("/publish")
async def publish(req: IdReq, user=Depends(get_current_user)):
    tpl = await template_service.detail(req.id)
    if not tpl:
        return fail("模板不存在")
    passed, reason = await check_text_security(
        collect_text({"title": tpl.get("title"), "content": tpl.get("content")}),
        user.get("openid", ""), scene=4, title=tpl.get("title") or "",
    )
    if not passed:
        return fail(reason)
    ok_pub = await template_service.publish(user["user_id"], req.id)
    if not ok_pub:
        return fail("该模板已被其他用户发布")
    return ok({"published": True})


@router.get("/published")
async def published(user=Depends(get_current_user)):
    return ok({"list": await template_service.published(user["user_id"])})
