from sqlalchemy import select

from app.database import SessionLocal
from app.models import Trip


class TripService:
    def _to_dict(self, r: Trip) -> dict:
        return {
            "id": r.id,
            "title": r.title,
            "city": r.city,
            "days": r.days,
            "route_type": r.route_type,
            "crowd_type": r.crowd_type,
            "budget_level": r.budget_level,
            "total_budget": r.total_budget,
            "status": r.status,
            "created_at": int(r.created_at.timestamp()),
            "content": r.content,
        }

    async def list(self, user_id: int, status: str = None):
        async with SessionLocal() as s:
            q = select(Trip).where(Trip.user_id == user_id, Trip.status != "deleted")
            if status:
                q = q.where(Trip.status == status)
            q = q.order_by(Trip.created_at.desc())
            rows = (await s.execute(q)).scalars().all()
            return [self._to_dict(r) for r in rows]

    async def detail(self, trip_id: int, user_id: int):
        async with SessionLocal() as s:
            r = (
                await s.execute(select(Trip).where(Trip.id == trip_id, Trip.user_id == user_id))
            ).scalar_one_or_none()
            return self._to_dict(r) if r else None

    async def save(self, user_id: int, trip: dict) -> int:
        content = trip.get("content", {})
        tid = trip.get("id")
        async with SessionLocal() as s:
            # 已存在且属于该用户 → 更新原行程（对话微调后落库）
            if tid:
                r = (
                    await s.execute(
                        select(Trip).where(Trip.id == int(tid), Trip.user_id == user_id)
                    )
                ).scalar_one_or_none()
                if r:
                    r.title = trip.get("title", r.title)
                    r.city = trip.get("city", r.city)
                    r.days = trip.get("days", r.days)
                    r.route_type = trip.get("route_type", r.route_type)
                    r.crowd_type = trip.get("crowd_type", r.crowd_type)
                    r.budget_level = trip.get("budget_level", r.budget_level)
                    r.total_budget = content.get("total_budget", r.total_budget)
                    r.content = content
                    await s.commit()
                    return r.id
            # 否则新建
            obj = Trip(
                user_id=user_id,
                title=trip.get("title", "我的行程"),
                city=trip.get("city", ""),
                days=trip.get("days", 1),
                route_type=trip.get("route_type", "popular"),
                crowd_type=trip.get("crowd_type", "朋友"),
                budget_level=trip.get("budget_level", "舒适"),
                total_budget=content.get("total_budget", 0),
                content=content,
            )
            s.add(obj)
            await s.commit()
            await s.refresh(obj)
            return obj.id

    async def delete(self, trip_id: int, user_id: int):
        async with SessionLocal() as s:
            r = (
                await s.execute(select(Trip).where(Trip.id == trip_id, Trip.user_id == user_id))
            ).scalar_one_or_none()
            if r:
                r.status = "deleted"
                await s.commit()


trip_service = TripService()
