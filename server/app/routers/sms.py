from fastapi import APIRouter

from app.schemas import SmsSendReq, ok, fail
from app.services import sms_service

router = APIRouter(prefix="/api/sms", tags=["sms"])


@router.post("/send")
async def send_code(req: SmsSendReq):
    """发送短信验证码。

    未配置短信 key 时返回 dev_code（开发模式），前端据此提示用户当前验证码；
    已配置 key 时不返回 code。
    """
    try:
        dev_code = await sms_service.gen_and_send(req.phone)
    except Exception as e:
        return fail(str(e))
    return ok({"dev_code": dev_code} if dev_code else None)
