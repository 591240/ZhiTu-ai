import time

from sqlalchemy import select, func

from app.database import SessionLocal
from app.models import Order, User
from app.services.distribution_service import distribution_service

PLANS = {
    "month": {"type": "month", "name": "月度会员", "price": 19.9},
    "year": {"type": "year", "name": "年度会员", "price": 129.0},
}


class PaymentService:
    def plans(self):
        return list(PLANS.values())

    async def create_order(self, user_id: int, plan_type: str, invite_code: str = None) -> dict:
        plan = PLANS.get(plan_type)
        if not plan:
            raise Exception("无效的套餐类型")
        order_no = f"BY{int(time.time())}{user_id:06d}"
        # 演示态：未接入微信支付商户号，直接计算到期时间供前端展示
        expire = int(time.time()) + (30 * 86400 if plan_type == "month" else 365 * 86400)
        async with SessionLocal() as s:
            order = Order(user_id=user_id, order_no=order_no, plan_type=plan_type, amount=plan["price"])
            s.add(order)
            await s.commit()
            await s.refresh(order)
            order_id = order.id

            # 分销佣金：根据邀请码解析邀请人并记录（演示态记为 pending）
            if invite_code:
                inviter = (await s.execute(
                    select(User.id).where(User.invite_code == invite_code.strip().upper())
                )).scalar_one_or_none()
                if inviter and inviter != user_id:
                    await distribution_service.record_commission(
                        inviter, user_id, plan["price"], "order", order_id
                    )
        # 真实环境：调用微信统一下单，返回 pay_params 供前端调起支付
        return {
            "order_no": order_no,
            "amount": plan["price"],
            "plan_type": plan_type,
            "vipExpireAt": expire,
            "demo": True,
            "pay_params": {},
        }


payment_service = PaymentService()
