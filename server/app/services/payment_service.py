import time
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Order, User
from app.services.distribution_service import distribution_service

PLANS = {
    "month": {"type": "month", "name": "月度会员", "price": 19.9, "days": 30},
    "year": {"type": "year", "name": "年度会员", "price": 129.0, "days": 365},
}


class PaymentService:
    def plans(self):
        return [{k: v for k, v in p.items() if k != "days"} for p in PLANS.values()]

    async def create_order(self, user_id: int, plan_type: str, invite_code: str = None) -> dict:
        plan = PLANS.get(plan_type)
        if not plan:
            raise Exception("无效的套餐类型")
        # 旧写法 BY{秒}{uid}：同一用户 1 秒内下两单就撞 order_no 唯一约束 → 500
        order_no = f"BY{int(time.time())}{uuid.uuid4().hex[:8].upper()}"
        async with SessionLocal() as s:
            order = Order(user_id=user_id, order_no=order_no, plan_type=plan_type,
                          amount=plan["price"], status="pending")
            s.add(order)
            await s.commit()
            await s.refresh(order)
            order_id = order.id

        # 佣金不在这里记：订单还是 pending，反复下单不付款就能白刷佣金。
        # 移到 mark_paid()（支付回调）里，且以库里绑定的邀请人为准。
        # 下单时带的邀请码只用来补绑关系（幂等：已绑定则忽略）。
        if invite_code:
            await distribution_service.bind(invite_code, user_id)
        return {
            "order_id": order_id,
            "order_no": order_no,
            "amount": plan["price"],
            "plan_type": plan_type,
            "demo": True,
            "pay_params": {},
        }

    async def mark_paid(self, order_no: str) -> dict:
        """支付回调入口：订单置为已支付、开通/续期会员、按邀请人记佣金。

        幂等：已支付的订单重复回调直接返回，不会重复加时长或重复记佣金。
        """
        async with SessionLocal() as s:
            order = (
                await s.execute(select(Order).where(Order.order_no == order_no))
            ).scalar_one_or_none()
            if not order:
                raise Exception("订单不存在")
            if order.status == "paid":
                return {"order_no": order_no, "status": "paid", "idempotent": True}

            plan = PLANS.get(order.plan_type)
            if not plan:
                raise Exception("订单套餐异常")

            user = (
                await s.execute(select(User).where(User.id == order.user_id))
            ).scalar_one_or_none()
            if not user:
                raise Exception("用户不存在")

            now = datetime.now()
            base = user.vip_expire_at if (user.vip_expire_at and user.vip_expire_at > now) else now
            user.is_vip = True
            user.vip_expire_at = base + timedelta(days=plan["days"])
            order.status = "paid"
            await s.commit()

            expire_at = user.vip_expire_at
            inviter_id = user.invited_by
            buyer_id = user.id
            amount = order.amount
            order_id = order.id

        if inviter_id:
            await distribution_service.record_commission(
                inviter_id, buyer_id, amount, "order", order_id
            )
        return {
            "order_no": order_no,
            "status": "paid",
            "vip_expire_at": int(expire_at.timestamp() * 1000),
        }


payment_service = PaymentService()
