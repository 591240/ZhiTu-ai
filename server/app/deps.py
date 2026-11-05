from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.utils.jwt_utils import decode_token


async def get_current_user(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """验签 + 查库。

    只验签是不够的：账号注销（is_active=False）后，旧 token 在 7 天有效期内
    仍然能调所有接口，注销等于形同虚设。这里每次请求回查一次状态，
    顺便把 openid 从库里取出来（内容安全校验必须用真实 openid，token 里可能是旧的）。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="token 无效")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="token 无效")

    row = (
        await session.execute(select(User).where(User.id == int(user_id)))
    ).scalar_one_or_none()
    if not row or not row.is_active:
        raise HTTPException(status_code=401, detail="账号不存在或已注销")

    return {
        "user_id": row.id,
        "openid": row.openid,
        "is_vip": bool(row.is_vip),
        "phone": row.phone or "",
    }
