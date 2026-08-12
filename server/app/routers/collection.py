from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.schemas import ok
from app.deps import get_current_user
from app.database import SessionLocal
from app.models import Collection

router = APIRouter(prefix="/api/collection", tags=["collection"])


@router.post("/add")
async def add(body: dict, user=Depends(get_current_user)):
    async with SessionLocal() as s:
        s.add(Collection(user_id=user["user_id"], template_id=int(body.get("template_id"))))
        await s.commit()
    return ok({})


@router.get("/list")
async def list_c(user=Depends(get_current_user)):
    async with SessionLocal() as s:
        rows = (await s.execute(select(Collection).where(Collection.user_id == user["user_id"]))).scalars().all()
        return ok({"list": [{"id": r.id, "template_id": r.template_id} for r in rows]})
