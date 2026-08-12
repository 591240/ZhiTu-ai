from fastapi import APIRouter, Depends

from app.schemas import LoginReq, BindPhoneReq, PhoneLoginReq, ok, fail
from app.services.auth_service import auth_service
from app.services import sms_service
from app.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(req: LoginReq):
    try:
        data = await auth_service.wechat_login(req.code, req.nickname, req.avatar, req.phone_code)
    except Exception as e:
        return fail(str(e))
    return ok(data)


@router.post("/bind-phone")
async def bind_phone(req: BindPhoneReq, user: dict = Depends(get_current_user)):
    try:
        data = await auth_service.bind_phone(user["user_id"], req.phone_code)
    except Exception as e:
        return fail(str(e))
    return ok(data)


# 手机号 + 短信验证码 登录 / 注册（与微信登录并存，phone 为账号关联键）
@router.post("/phone-login")
async def phone_login(req: PhoneLoginReq):
    ok_verify = await sms_service.verify(req.phone, req.code)
    if not ok_verify:
        return fail("验证码错误或已过期")
    try:
        data = await auth_service.phone_register_or_login(req.phone)
    except Exception as e:
        return fail(str(e))
    return ok(data)
