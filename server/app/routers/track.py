from fastapi import APIRouter, Depends

from app.schemas import ok, fail
from app.deps import get_current_user
from app.database import SessionLocal
from app.models import Event

router = APIRouter(prefix="/api/track", tags=["track"])


@router.post("")
async def track(body: dict, user=Depends(get_current_user)):
    """批量上报埋点事件。events: [{type, props}]。失败不阻塞主流程。"""
    events = body.get("events") or []
    if not isinstance(events, list) or not events:
        return ok({})
    uid = user.get("user_id")
    rows = []
    for e in events[:200]:  # 上限保护
        t = (e.get("type") or "").strip()
        if not t:
            continue
        props = e.get("props") or {}
        if not isinstance(props, dict):
            props = {"value": props}
        rows.append(Event(user_id=uid, event_type=t, props=props))
    if rows:
        async with SessionLocal() as s:
            s.add_all(rows)
            await s.commit()
    return ok({"count": len(rows)})
