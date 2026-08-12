from app.config import settings

redis_client = None
if settings.redis_url:
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
