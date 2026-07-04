from redis.asyncio import Redis

from .settings import settings

redis_client = Redis(
    host=settings.redis_client.host,
    port=settings.redis_client.port,
    db=settings.redis_client.db,
    decode_responses=True,
)
