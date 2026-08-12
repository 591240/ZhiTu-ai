import asyncio
import time

import httpx

from app.config import settings


async def code2session(code: str) -> dict:
    """微信 code 换 openid。无 AppID 时返回 mock openid，便于本地开发。"""
    if not settings.wx_app_id:
        return {"openid": "mock_openid_" + code[-6:]}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": settings.wx_app_id,
                "secret": settings.wx_app_secret,
                "js_code": code,
                "grant_type": "authorization_code",
            },
        )
        data = resp.json()
        if "openid" not in data:
            # 把微信返回的原始错误抛出去，方便定位是 invalid appid / code expired 等
            raise Exception(f"微信 jscode2session 失败：{data}")
        return data


# —— access_token 内存缓存（单进程够用；多实例生产建议改用 Redis 共享）——
_TOKEN_CACHE = {"token": None, "exp": 0.0}
_TOKEN_LOCK = asyncio.Lock()


async def get_access_token() -> str | None:
    """获取全局 access_token（微信限制每日 2000 次，必须缓存）。"""
    if not settings.wx_app_id:
        return None
    now = time.time()
    if _TOKEN_CACHE["token"] and _TOKEN_CACHE["exp"] > now + 60:
        return _TOKEN_CACHE["token"]
    async with _TOKEN_LOCK:
        # 双重检查，避免并发重复刷新
        if _TOKEN_CACHE["token"] and _TOKEN_CACHE["exp"] > now + 60:
            return _TOKEN_CACHE["token"]
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.weixin.qq.com/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": settings.wx_app_id,
                    "secret": settings.wx_app_secret,
                },
            )
            data = resp.json()
            if "access_token" not in data:
                raise Exception("获取 access_token 失败：" + str(data))
            _TOKEN_CACHE["token"] = data["access_token"]
            _TOKEN_CACHE["exp"] = now + float(data.get("expires_in", 7200))
            return _TOKEN_CACHE["token"]


async def get_phone_number(phone_code: str) -> str | None:
    """用手机号快速验证 code 换手机号（新版组件）。

    回调 detail.code -> 后端用 access_token 调 getuserphonenumber。
    无 AppID 时 mock 返回测试号，便于本地开发。
    任何失败返回 None（不阻断主登录流程）。
    """
    if not settings.wx_app_id:
        return "13800000000"
    if not phone_code:
        return None
    try:
        token = await get_access_token()
        if not token:
            return None
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.weixin.qq.com/wxa/business/getuserphonenumber",
                params={"access_token": token},
                json={"code": phone_code},
            )
            data = resp.json()
            if data.get("errcode") != 0:
                print("get_phone_number err:", data)
                return None
            return data.get("phone_info", {}).get("purePhoneNumber")
    except Exception as e:
        print("get_phone_number error:", e)
        return None
