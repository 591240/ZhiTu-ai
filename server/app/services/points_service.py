from sqlalchemy import select, update

from app.config import settings
from app.database import SessionLocal
from app.models import User


class PointsService:
    """用户积分服务：查询、扣减、人工充值申请。"""

    async def get_points(self, user_id: int) -> int:
        async with SessionLocal() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one_or_none()
            return user.points if user else 0

    async def consume(self, user_id: int, cost: int) -> bool:
        """扣减积分，余额不足返回 False。

        必须用带条件的原子 UPDATE：读-改-写会让并发请求都读到同一个旧余额，
        同一笔积分被扣两次（用户点两下就能白嫖一次生成）。
        """
        if cost <= 0:
            return True
        async with SessionLocal() as session:
            res = await session.execute(
                update(User)
                .where(User.id == user_id, User.points >= cost)
                .values(points=User.points - cost)
            )
            await session.commit()
            return (res.rowcount or 0) > 0

    async def consume_plan(self, user_id: int) -> bool:
        return await self.consume(user_id, settings.points_per_plan)

    async def consume_chat(self, user_id: int) -> bool:
        return await self.consume(user_id, settings.points_per_chat)

    async def add_points(self, user_id: int, points: int) -> int:
        """管理员/充值成功后增加积分，返回新余额。"""
        if points == 0:
            return await self.get_points(user_id)
        async with SessionLocal() as session:
            await session.execute(
                update(User).where(User.id == user_id).values(points=User.points + points)
            )
            await session.commit()
            row = (
                await session.execute(select(User.points).where(User.id == user_id))
            ).scalar_one_or_none()
            return row or 0


points_service = PointsService()
