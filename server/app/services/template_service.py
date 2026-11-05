from sqlalchemy import select, func
from fastapi.concurrency import run_in_threadpool

from app.database import SessionLocal
from app.models import Template
from app.services.plan_service import gen_trip

SEED = [
    {"title": "杭州2日经典西湖游", "city": "杭州", "days": 2, "route_type": "popular", "cover": "🏞️"},
    {"title": "成都3日小众文艺游", "city": "成都", "days": 3, "route_type": "niche", "cover": "🐼"},
    {"title": "西安2日美食历史游", "city": "西安", "days": 2, "route_type": "popular", "cover": "🏯"},
    {"title": "苏州1日园林精华游", "city": "苏州", "days": 1, "route_type": "popular", "cover": "🌿"},
]


class TemplateService:
    def _to_dict(self, r: Template) -> dict:
        return {
            "id": r.id,
            "title": r.title,
            "city": r.city,
            "days": r.days,
            "route_type": r.route_type,
            "cover": r.cover,
            "uses": r.uses,
            "spots_count": r.spots_count,
            "author_id": r.author_id,
            "is_published": bool(r.author_id),
            "content": r.content,
        }

    async def hot(self):
        async with SessionLocal() as s:
            rows = (await s.execute(select(Template).order_by(Template.uses.desc()).limit(10))).scalars().all()
            return [self._to_dict(r) for r in rows]

    async def detail(self, tid: int):
        async with SessionLocal() as s:
            r = (await s.execute(select(Template).where(Template.id == tid))).scalar_one_or_none()
            return self._to_dict(r) if r else None

    async def use(self, tid: int):
        async with SessionLocal() as s:
            r = (await s.execute(select(Template).where(Template.id == tid))).scalar_one_or_none()
            if not r:
                return None
            r.uses = (r.uses or 0) + 1
            await s.commit()
            return r.content

    async def publish(self, user_id: int, tid: int) -> bool:
        """将模板发布到广场（标记为当前用户所发布）。

        只能认领自己创建的模板：种子模板的 author_id 为空，任何人第一次"发布"
        就能把它变成自己的；而别人已发布的模板更是能被直接改走归属。
        """
        async with SessionLocal() as s:
            r = (await s.execute(select(Template).where(Template.id == tid))).scalar_one_or_none()
            if not r:
                return False
            if r.author_id is not None and r.author_id != user_id:
                return False
            r.author_id = user_id
            await s.commit()
            return True

    async def published(self, user_id: int):
        """返回当前用户发布到广场的模板列表。"""
        async with SessionLocal() as s:
            rows = (
                await s.execute(
                    select(Template)
                    .where(Template.author_id == user_id)
                    .order_by(Template.created_at.desc())
                )
            ).scalars().all()
            return [self._to_dict(r) for r in rows]

    async def seed(self):
        async with SessionLocal() as s:
            cnt = (await s.execute(select(func.count()).select_from(Template))).scalar()
            if cnt and cnt > 0:
                return
            for item in SEED:
                # gen_trip 内部会打高德 POI/公交接口（同步 requests），必须离开事件循环
                content = (
                    await run_in_threadpool(
                        gen_trip,
                        {"city": item["city"], "days": item["days"], "route_type": item["route_type"]},
                    )
                )["content"]
                s.add(Template(
                    title=item["title"], city=item["city"], days=item["days"],
                    route_type=item["route_type"], cover=item["cover"],
                    spots_count=len(content["itinerary"]) * 3, content=content, uses=100,
                ))
            await s.commit()


template_service = TemplateService()
