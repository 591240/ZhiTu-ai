import datetime
import logging

from app.config import settings
from app.redis_client import redis_client

logger = logging.getLogger(__name__)


class QuotaService:
    """免费用户每日 AI 行程生成限流。Redis 不可用时回退到内存字典兜底。"""

    _mem: dict = {}

    def _mem_check(self, user_id: int, today: str) -> bool:
        key = f"{user_id}:{today}"
        cur = self._mem.get(key, 0)
        if cur >= settings.daily_plan_limit:
            return False
        self._mem[key] = cur + 1
        return True

    def _mem_remaining(self, user_id: int, today: str) -> int:
        cur = self._mem.get(f"{user_id}:{today}", 0)
        return max(0, settings.daily_plan_limit - cur)

    async def check_and_consume(self, user_id: int, is_vip: bool) -> bool:
        if is_vip:
            return True
        today = datetime.datetime.now().strftime("%Y%m%d")
        if redis_client:
            try:
                key = f"user:daily_count:{user_id}:{today}"
                cur = int(await redis_client.get(key) or 0)
                if cur >= settings.daily_plan_limit:
                    return False
                await redis_client.incr(key)
                return True
            except Exception:
                logger.warning("Redis 不可用，限额回退到内存计数")
                return self._mem_check(user_id, today)
        return self._mem_check(user_id, today)

    async def get_remaining(self, user_id: int, is_vip: bool) -> int:
        if is_vip:
            return -1
        today = datetime.datetime.now().strftime("%Y%m%d")
        if redis_client:
            try:
                cur = int(await redis_client.get(f"user:daily_count:{user_id}:{today}") or 0)
                return max(0, settings.daily_plan_limit - cur)
            except Exception:
                logger.warning("Redis 不可用，限额回退到内存计数")
                return self._mem_remaining(user_id, today)
        return self._mem_remaining(user_id, today)


quota_service = QuotaService()
