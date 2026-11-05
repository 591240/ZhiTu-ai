import asyncio
import logging
import time

import httpx

from app.config import settings
from app.redis_client import redis_client

logger = logging.getLogger(__name__)

# msg_sec_check v2 的 content 上限（超出会被微信直接拒）
_SEC_MAX_CHARS = 2500
# access_token 的 Redis key。多 worker 部署时必须共享——
# 各进程各缓存一份会同时刷新，既浪费每日 2000 次的获取限额，
# 也可能在旧 token 刚失效时拿到彼此尚未生效的值。
_TOKEN_KEY = "wx:access_token"
_TOKEN_REDIS_TTL = 7000  # 略小于微信的 7200，留足安全余量


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


# —— access_token 缓存：Redis 优先，进程内兜底 ——
# 单 worker 时进程内就够；多 worker 必须靠 Redis 共享，否则每个进程各刷新一次。
_TOKEN_CACHE = {"token": None, "exp": 0.0}
_TOKEN_LOCK = asyncio.Lock()


async def _redis_get_token() -> str | None:
    if not redis_client:
        return None
    try:
        val = await redis_client.get(_TOKEN_KEY)
        if not val:
            return None
        ttl = await redis_client.ttl(_TOKEN_KEY)
        if ttl is not None and ttl <= 60:
            return None
        return val
    except Exception as e:
        logger.warning("读取 access_token 缓存失败，退回进程内缓存: %s", e)
        return None


async def _redis_set_token(token: str) -> None:
    if not redis_client:
        return
    try:
        await redis_client.set(_TOKEN_KEY, token, ex=_TOKEN_REDIS_TTL)
    except Exception as e:
        logger.warning("写入 access_token 缓存失败: %s", e)


async def get_access_token() -> str | None:
    """获取全局 access_token（微信限制每日 2000 次，必须缓存）。"""
    if not settings.wx_app_id:
        return None

    cached = await _redis_get_token()
    if cached:
        return cached

    now = time.time()
    if _TOKEN_CACHE["token"] and _TOKEN_CACHE["exp"] > now + 60:
        return _TOKEN_CACHE["token"]

    async with _TOKEN_LOCK:
        # 双重检查：等锁期间可能已被同进程其他协程刷新
        cached = await _redis_get_token()
        if cached:
            return cached
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
            token = data["access_token"]
            _TOKEN_CACHE["token"] = token
            _TOKEN_CACHE["exp"] = now + float(data.get("expires_in", 7200))
            await _redis_set_token(token)
            return token


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


async def check_text_security(content: str, openid: str = "", scene: int = 2, title: str = "") -> tuple[bool, str]:
    """微信内容安全校验（msg_sec_check v2），返回 (是否放行, 拒绝文案)。

    scene：1=资料 2=评论 3=论坛 4=社交日志。
    放行优先于拦截：未配 AppID/Secret、微信接口异常、或返回 87030（无法判定）时一律放行，
    只有明确 risky 才阻断——审核接口抖动不该让用户提交不了行程。
    """
    text = (content or "").strip()
    if not text or not settings.wx_app_id or not settings.wx_app_secret:
        return True, ""
    # v2 接口强制要求真实 openid（需近期访问过小程序），否则只会拿到 40003 invalid openid
    if not openid or openid.startswith("mock_"):
        logger.debug("跳过 msg_sec_check：无有效 openid（开发态）")
        return True, ""
    try:
        token = await get_access_token()
        if not token:
            return True, ""
        payload = {"content": text[:_SEC_MAX_CHARS], "version": "2", "scene": scene}
        if title:
            payload["title"] = title[:60]
        if openid:
            payload["openid"] = openid
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "https://api.weixin.qq.com/wxa/msg_sec_check",
                params={"access_token": token},
                json=payload,
            )
            data = resp.json()
        errcode = data.get("errcode", 0)
        if errcode == 87030:
            return True, ""
        if errcode != 0:
            logger.warning("msg_sec_check 接口返回异常，放行处理: %s", data)
            return True, ""
        result = data.get("result") or {}
        if result.get("suggest") == "risky":
            logger.info("msg_sec_check 拦截 scene=%s label=%s", scene, result.get("label"))
            return False, "内容含违规信息，请修改后再提交"
        if result.get("suggest") == "review":
            logger.info("msg_sec_check 建议复审 scene=%s label=%s", scene, result.get("label"))
        return True, ""
    except Exception as e:
        logger.warning("msg_sec_check 调用失败，放行处理: %s", e)
        return True, ""


def collect_text(obj, limit: int = _SEC_MAX_CHARS) -> str:
    """把嵌套 dict/list 里的字符串拼成一段纯文本，供内容安全校验用。"""
    out: list[str] = []
    n = 0

    def walk(x):
        nonlocal n
        if n >= limit:
            return
        if isinstance(x, str):
            s = x.strip()
            if s:
                out.append(s)
                n += len(s)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)

    walk(obj)
    return " ".join(out)[:limit]
