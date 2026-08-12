from fastapi import Depends, Header, HTTPException

from app.utils.jwt_utils import decode_token


async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="token 无效")
