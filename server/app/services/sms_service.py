import asyncio
import random
import re
import time

from app.redis_client import redis_client
from app.utils import sms as sms_util

# 内存兜底（redis 不可用时使用），保证服务不崩
_MEM: dict = {}
_MEM_LOCK = asyncio.Lock()

CODE_TTL = 5 * 60        # 验证码有效期 5 分钟
SEND_INTERVAL = 60       # 同手机号 60 秒内只能发一次
PHONE_RE = re.compile(r"^1[3-9]\d{9}$")

# Redis 可用性标志：初始乐观（客户端对象存在即认为可用）；
# 首次 redis 操作抛异常即永久降级内存，避免反复超时阻塞请求。
_redis_ok = redis_client is not None


def _now() -> float:
    return time.time()


async def _set(key: str, val: str, ex: int = None) -> bool:
    """写入 Redis；失败则标记降级并返回 False（由调用方写内存）。"""
    global _redis_ok
    if not _redis_ok:
        return False
    try:
        if ex:
            await redis_client.set(key, val, ex=ex)
        else:
            await redis_client.set(key, val)
        return True
    except Exception as e:
        print(f"[SMS] Redis 不可用，降级内存存储：{e}")
        _redis_ok = False
        return False


async def _get(key: str):
    global _redis_ok
    if not _redis_ok:
        return None
    try:
        return await redis_client.get(key)
    except Exception as e:
        print(f"[SMS] Redis 不可用，降级内存存储：{e}")
        _redis_ok = False
        return None


async def _ttl(key: str) -> int:
    global _redis_ok
    if not _redis_ok:
        return 0
    try:
        return await redis_client.ttl(key) or 0
    except Exception as e:
        print(f"[SMS] Redis 不可用，降级内存存储：{e}")
        _redis_ok = False
        return 0


async def _del(key: str):
    global _redis_ok
    if not _redis_ok:
        return
    try:
        await redis_client.delete(key)
    except Exception as e:
        print(f"[SMS] Redis 不可用，降级内存存储：{e}")
        _redis_ok = False


async def gen_and_send(phone: str):
    """生成验证码、发送短信、写入存储。返回 dev_code（开发态展示用，生产为 None）。"""
    if not PHONE_RE.match(phone):
        raise Exception("手机号格式不正确")

    # —— 频率限制（Redis 优先，内存兜底）——
    ttl = await _ttl(f"sms:limit:{phone}")
    if ttl and ttl > 0:
        raise Exception(f"请 {ttl} 秒后再获取验证码")
    if not _redis_ok:
        async with _MEM_LOCK:
            last = _MEM.get(f"sms:limit:{phone}")
            if last and _now() - last < SEND_INTERVAL:
                raise Exception("操作频繁，请稍后再试")

    code = f"{random.randint(100000, 999999)}"
    success, dev_code = await sms_util.send_sms(phone, code)
    if not success:
        raise Exception("短信发送失败，请稍后重试")

    # —— 落库 ——
    if not await _set(f"sms:code:{phone}", code, ex=CODE_TTL):
        async with _MEM_LOCK:
            _MEM[f"sms:code:{phone}"] = (code, _now() + CODE_TTL)
    if not await _set(f"sms:limit:{phone}", "1", ex=SEND_INTERVAL):
        async with _MEM_LOCK:
            _MEM[f"sms:limit:{phone}"] = _now()

    return dev_code


async def verify(phone: str, code: str) -> bool:
    """校验验证码（一次性，成功即删除）。"""
    if not code:
        return False
    stored = await _get(f"sms:code:{phone}")
    if stored and stored == code:
        await _del(f"sms:code:{phone}")
        return True
    if not _redis_ok:
        async with _MEM_LOCK:
            item = _MEM.get(f"sms:code:{phone}")
            if item and item[0] == code and item[1] > _now():
                del _MEM[f"sms:code:{phone}"]
                return True
    return False
