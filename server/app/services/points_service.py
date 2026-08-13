from sqlalchemy import select

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
        """扣减积分，余额不足返回 False。"""
        async with SessionLocal() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one_or_none()
            if not user:
                return False
            if user.points < cost:
                return False
            user.points -= cost
            await session.commit()
            return True

    async def consume_plan(self, user_id: int) -> bool:
        return await self.consume(user_id, settings.points_per_plan)

    async def consume_chat(self, user_id: int) -> bool:
        return await self.consume(user_id, settings.points_per_chat)

    async def add_points(self, user_id: int, points: int) -> int:
        """管理员/充值成功后增加积分，返回新余额。"""
        async with SessionLocal() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one_or_none()
            if not user:
                return 0
            user.points += points
            await session.commit()
            return user.points


points_service = PointsService()
