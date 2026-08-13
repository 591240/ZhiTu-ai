from fastapi import APIRouter, Depends

from app.schemas import PlanFormReq, PlanQuickReq, AdjustReq, ok, fail
from app.deps import get_current_user
from app.services.plan_service import plan_service
from app.services.points_service import points_service

router = APIRouter(prefix="/api/plan", tags=["plan"])


@router.post("/form")
async def plan_form(req: PlanFormReq, user=Depends(get_current_user)):
    if not await points_service.consume_plan(user["user_id"]):
        return fail("积分不足，请充值后再生成行程", code=4001)
    trip = await plan_service.generate_from_form(req)
    return ok({"trip": {"id": "gen", **trip}})


@router.post("/quick")
async def plan_quick(req: PlanQuickReq, user=Depends(get_current_user)):
    if not await points_service.consume_plan(user["user_id"]):
        return fail("积分不足，请充值后再生成行程", code=4001)
    trip = await plan_service.generate_from_quick(req.text)
    return ok({"trip": {"id": "gen", **trip}})


@router.post("/chat-adjust")
async def adjust(req: AdjustReq, user=Depends(get_current_user)):
    reply, trip = await plan_service.adjust(req.trip, req.instruction)
    return ok({"trip": trip, "reply": reply})
