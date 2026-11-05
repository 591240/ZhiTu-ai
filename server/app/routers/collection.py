from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.deps import get_current_user
from app.models import Collection, Template
from app.schemas import CollectionAddReq, ok, fail

router = APIRouter(prefix="/api/collection", tags=["collection"])


@router.post("/add")
async def add(
    req: CollectionAddReq,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    exists = (
        await session.execute(select(Template.id).where(Template.id == req.template_id))
    ).scalar_one_or_none()
    if not exists:
        return fail("模板不存在", code=404)

    dup = (
        await session.execute(
            select(Collection.id).where(
                Collection.user_id == user["user_id"],
                Collection.template_id == req.template_id,
            )
        )
    ).scalar_one_or_none()
    if dup:
        return ok({"collected": True, "duplicated": True})

    session.add(Collection(user_id=user["user_id"], template_id=req.template_id))
    try:
        await session.commit()
    except IntegrityError:
        # 并发重复点收藏：唯一索引兜底，按已收藏处理
        await session.rollback()
    return ok({"collected": True})


@router.get("/list")
async def list_c(user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """返回收藏的完整模板。

    早先只返回 {id, template_id}，而收藏页渲染的是 title/city/cover/days，
    且点击时把「收藏记录 id」当成模板 id 传下去——关掉 mock 后整页空白 + 点进去 404。
    """
    rows = (
        await session.execute(
            select(Template, Collection.id)
            .join(Collection, Collection.template_id == Template.id)
            .where(Collection.user_id == user["user_id"])
            .order_by(Collection.created_at.desc())
        )
    ).all()
    return ok({"list": [{
        "id": tpl.id,                 # 模板 id，前端直接拿去开详情
        "collection_id": cid,
        "title": tpl.title,
        "city": tpl.city,
        "days": tpl.days,
        "cover": tpl.cover,
        "route_type": tpl.route_type,
        "uses": tpl.uses,
        "spots_count": tpl.spots_count,
    } for tpl, cid in rows]})
