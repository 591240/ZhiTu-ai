from fastapi import APIRouter, Depends

from app.schemas import PlanFormReq, PlanQuickReq, AdjustReq, ok, fail
from app.deps import get_current_user
from app.services.plan_service import plan_service
from app.services.points_service import points_service
from app.services.quota_service import quota_service
from app.config import settings

router = APIRouter(prefix="/api/plan", tags=["plan"])


async def _guard(user: dict):
    """生成前的配额/积分闸门，返回 None 表示放行，否则返回 fail 响应。

    顺序：先扣每日配额（便宜），再扣积分；积分不足时把配额回滚，
    不能让用户白掉一次当日额度。
    """
    uid, vip = user["user_id"], bool(user.get("is_vip"))
    if not await quota_service.check_and_consume(uid, vip):
        return fail(
            f"今日免费生成次数已用完（每天 {settings.daily_plan_limit} 次），明天再来或开通会员",
            code=4002,
        )
    if settings.monetization_enabled and not await points_service.consume_plan(uid):
        await quota_service.release(uid, vip)
        return fail("积分不足，请充值后再生成行程", code=4001)
    return None


@router.post("/form")
async def plan_form(req: PlanFormReq, user=Depends(get_current_user)):
    blocked = await _guard(user)
    if blocked:
        return blocked
    trip = await plan_service.generate_from_form(req)
    return ok({"trip": {"id": None, **trip}})


@router.post("/quick")
async def plan_quick(req: PlanQuickReq, user=Depends(get_current_user)):
    blocked = await _guard(user)
    if blocked:
        return blocked
    trip = await plan_service.generate_from_quick(req.text)
    return ok({"trip": {"id": None, **trip}})


@router.post("/chat-adjust")
async def adjust(req: AdjustReq, user=Depends(get_current_user)):
    # 微调同样会调大模型：变现开启时必须计费，否则 form/quick 扣积分、微调免费，
    # 用户靠反复微调就能绕过计费。
    if settings.monetization_enabled and not await points_service.consume_chat(user["user_id"]):
        return fail("积分不足，请充值后再调整行程", code=4001)
    reply, trip = await plan_service.adjust(req.trip, req.instruction)
    return ok({"trip": trip, "reply": reply})
