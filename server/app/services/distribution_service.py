"""分销佣金（CPS）服务。

- 每个用户拥有唯一邀请码（invite_code）
- 被邀请人通过邀请码注册/付费，邀请人获得佣金
- 当前佣金在「会员付费(order)」时按 commission_rate 记录为 pending（演示态，真实结算接入微信支付后转为 settled）
"""
import random
import string

from sqlalchemy import select, func, text

from app.database import SessionLocal
from app.models import User, DistributionRecord
from app.config import settings


def _gen_code(n: int = None) -> str:
    n = n or settings.invite_code_len
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=n))


class DistributionService:
    async def ensure_code(self, user_id: int) -> str:
        async with SessionLocal() as s:
            u = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            if not u:
                # 早先这里会在 else 分支里重复查一次再直接取属性，用户不存在时抛 AttributeError
                return ""
            if u.invite_code:
                return u.invite_code
            # 生成唯一码
            for _ in range(20):
                code = _gen_code()
                dup = (await s.execute(
                    select(User.id).where(User.invite_code == code)
                )).scalar_one_or_none()
                if not dup:
                    u.invite_code = code
                    await s.commit()
                    return code
        return _gen_code()

    async def bind(self, invite_code: str, user_id: int) -> dict:
        invite_code = (invite_code or "").strip().upper()
        if not invite_code:
            return {"ok": False, "message": "邀请码不能为空"}
        async with SessionLocal() as s:
            me = (await s.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            if not me:
                return {"ok": False, "message": "用户不存在"}
            if me.invited_by:
                return {"ok": True, "message": "已绑定邀请人", "invited_by": me.invited_by}
            inviter = (await s.execute(
                select(User).where(User.invite_code == invite_code)
            )).scalar_one_or_none()
            if not inviter:
                return {"ok": False, "message": "邀请码无效"}
            if inviter.id == user_id:
                return {"ok": False, "message": "不能绑定自己的邀请码"}
            me.invited_by = inviter.id
            await s.commit()
        return {"ok": True, "message": "绑定成功", "invited_by": inviter.id}

    async def record_commission(self, distributor_id: int, from_user_id: int,
                                amount: float, ref_type: str, ref_id: int = 0) -> float:
        """记录一笔佣金（pending）。返回佣金金额。distributor_id 无效则跳过。"""
        if not distributor_id or distributor_id == from_user_id:
            return 0.0
        commission = round(amount * settings.commission_rate, 2)
        async with SessionLocal() as s:
            rec = DistributionRecord(
                distributor_id=distributor_id,
                from_user_id=from_user_id,
                ref_type=ref_type,
                ref_id=ref_id,
                amount=amount,
                commission=commission,
                status="pending",
            )
            s.add(rec)
            await s.commit()
        return commission

    async def my(self, user_id: int) -> dict:
        code = await self.ensure_code(user_id)
        async with SessionLocal() as s:
            invited_count = (await s.execute(
                select(func.count()).select_from(User).where(User.invited_by == user_id)
            )).scalar() or 0
            commission_total = (await s.execute(
                select(func.coalesce(func.sum(DistributionRecord.commission), 0.0))
                .where(DistributionRecord.distributor_id == user_id)
            )).scalar() or 0.0
            rows = (await s.execute(
                select(DistributionRecord)
                .where(DistributionRecord.distributor_id == user_id)
                .order_by(DistributionRecord.id.desc())
                .limit(50)
            )).scalars().all()
            records = [{
                "id": r.id,
                "ref_type": r.ref_type,
                "amount": r.amount,
                "commission": r.commission,
                "status": r.status,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            } for r in rows]
        return {
            "invite_code": code,
            "invited_count": invited_count,
            "commission_total": round(float(commission_total), 2),
            "commission_rate": settings.commission_rate,
            "records": records,
        }


distribution_service = DistributionService()
