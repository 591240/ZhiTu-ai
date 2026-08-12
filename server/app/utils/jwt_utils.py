import datetime

import jwt

from app.config import settings


def create_token(payload: dict) -> str:
    payload = dict(payload)
    payload["exp"] = datetime.datetime.utcnow() + datetime.timedelta(hours=settings.jwt_expire_hours)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
