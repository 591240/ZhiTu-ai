from fastapi import APIRouter, Depends

from app.schemas import ok, fail
from app.deps import get_current_user
from app.services.payment_service import payment_service

router = APIRouter(prefix="/api/membership", tags=["membership"])


@router.get("/plans")
async def plans(user=Depends(get_current_user)):
    return ok({"plans": payment_service.plans()})


@router.post("/order")
async def order(body: dict, user=Depends(get_current_user)):
    try:
        data = await payment_service.create_order(
            user["user_id"], body.get("plan_type"), body.get("invite_code")
        )
    except Exception as e:
        return fail(str(e))
    return ok(data)
