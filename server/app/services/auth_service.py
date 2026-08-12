from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.utils.jwt_utils import create_token
from app.utils.wechat import code2session, get_phone_number


class AuthService:
    async def wechat_login(self, code: str, nickname: str = None, avatar: str = None, phone_code: str = None):
        data = await code2session(code)
        openid = data.get("openid")
        if not openid:
            raise Exception("微信登录失败：未获取到 openid")

        async with SessionLocal() as session:
            user = (
                await session.execute(select(User).where(User.openid == openid))
            ).scalar_one_or_none()
            if not user:
                user = User(openid=openid, nickname=nickname or "微信用户", avatar=avatar or "")
                session.add(user)
                await session.commit()
                await session.refresh(user)
            if not user.is_active:
                raise Exception("账号已注销")
            # 更新头像/昵称（首次授权或用户主动更新时）
            if nickname and (not user.nickname or user.nickname == "微信用户"):
                user.nickname = nickname.strip()
            if avatar and not user.avatar:
                user.avatar = avatar.strip()
            # 手机号绑定：仅在用户尚未绑定且本次传来 phone_code 时
            if phone_code and not user.phone:
                phone = await get_phone_number(phone_code)
                if phone:
                    user.phone = phone
                    await session.commit()
            await session.commit()
            await session.refresh(user)
            token = create_token({"user_id": user.id, "openid": user.openid})
            return {
                "token": token,
                "user": {
                    "id": user.id,
                    "nickname": user.nickname,
                    "avatar": user.avatar,
                    "phone": user.phone or "",
                    "city": user.city,
                    "is_vip": user.is_vip,
                },
            }

    async def bind_phone(self, user_id: int, phone_code: str):
        """已登录用户绑定/更换手机号。"""
        phone = await get_phone_number(phone_code)
        if not phone:
            raise Exception("手机号获取失败，请重试")
        async with SessionLocal() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one_or_none()
            if not user:
                raise Exception("用户不存在")
            user.phone = phone
            await session.commit()
            return {"phone": phone}

    async def phone_register_or_login(self, phone: str):
        """手机号验证码登录/注册：按 phone 查用户，无则注册新用户，返回 token。

        与微信登录并存——同一手机号无论通过微信绑定还是短信注册都归并到同一账号。
        """
        async with SessionLocal() as session:
            user = (
                await session.execute(select(User).where(User.phone == phone))
            ).scalar_one_or_none()
            if not user:
                user = User(
                    openid=f"sms_{phone}",
                    nickname=f"用户{phone[-4:]}",
                    phone=phone,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            if not user.is_active:
                raise Exception("账号已注销")
            token = create_token({"user_id": user.id, "openid": user.openid})
            return {
                "token": token,
                "user": {
                    "id": user.id,
                    "nickname": user.nickname,
                    "avatar": user.avatar,
                    "phone": user.phone or "",
                    "city": user.city,
                    "is_vip": user.is_vip,
                },
            }


auth_service = AuthService()
