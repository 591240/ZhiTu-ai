import datetime
import logging

from app.config import settings
from app.redis_client import redis_client

logger = logging.getLogger(__name__)


class QuotaService:
    """免费用户每日 AI 行程生成限流。Redis 不可用时回退到内存字典兜底。

    注意：进程内计数只适合单 worker。多 worker / 多实例部署必须配 Redis，
    否则每个进程各算一份，实际额度是 limit × worker 数。
    """

    _mem: dict = {}

    @staticmethod
    def _today() -> str:
        return datetime.datetime.now().strftime("%Y%m%d")

    def _mem_key(self, user_id: int, today: str) -> str:
        return f"{user_id}:{today}"

    def _mem_sweep(self, today: str) -> None:
        """丢掉过期日期的计数，避免内存字典随天数无界增长。"""
        if len(self._mem) < 5000:
            return
        for k in [k for k in self._mem if not k.endswith(today)]:
            self._mem.pop(k, None)

    def _mem_check(self, user_id: int, today: str) -> bool:
        key = self._mem_key(user_id, today)
        cur = self._mem.get(key, 0)
        if cur >= settings.daily_plan_limit:
            return False
        self._mem[key] = cur + 1
        self._mem_sweep(today)
        return True

    def _mem_remaining(self, user_id: int, today: str) -> int:
        cur = self._mem.get(self._mem_key(user_id, today), 0)
        return max(0, settings.daily_plan_limit - cur)

    def _redis_key(self, user_id: int, today: str) -> str:
        return f"user:daily_count:{user_id}:{today}"

    async def check_and_consume(self, user_id: int, is_vip: bool = False) -> bool:
        if is_vip or settings.daily_plan_limit <= 0:
            return True
        today = self._today()
        if redis_client:
            try:
                key = self._redis_key(user_id, today)
                cur = int(await redis_client.get(key) or 0)
                if cur >= settings.daily_plan_limit:
                    return False
                await redis_client.incr(key)
                await redis_client.expire(key, 86400)
                return True
            except Exception:
                logger.warning("Redis 不可用，限额回退到内存计数")
                return self._mem_check(user_id, today)
        return self._mem_check(user_id, today)

    async def release(self, user_id: int, is_vip: bool = False) -> None:
        """回滚一次配额（扣积分失败等场景，避免用户白占一次额度）。"""
        if is_vip or settings.daily_plan_limit <= 0:
            return
        today = self._today()
        if redis_client:
            try:
                key = self._redis_key(user_id, today)
                cur = int(await redis_client.get(key) or 0)
                if cur > 0:
                    await redis_client.decr(key)
                return
            except Exception:
                logger.warning("Redis 不可用，限额回退到内存计数")
        key = self._mem_key(user_id, today)
        if self._mem.get(key, 0) > 0:
            self._mem[key] -= 1

    async def get_remaining(self, user_id: int, is_vip: bool = False) -> int:
        if is_vip:
            return -1
        today = self._today()
        if redis_client:
            try:
                cur = int(await redis_client.get(self._redis_key(user_id, today)) or 0)
                return max(0, settings.daily_plan_limit - cur)
            except Exception:
                logger.warning("Redis 不可用，限额回退到内存计数")
                return self._mem_remaining(user_id, today)
        return self._mem_remaining(user_id, today)


quota_service = QuotaService()
