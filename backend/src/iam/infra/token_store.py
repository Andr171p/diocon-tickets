import json
from datetime import timedelta
from uuid import UUID

from redis.asyncio import Redis

from src.shared.utils.time import current_datetime


class RedisTokenStore:
    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client

    @staticmethod
    def _build_key(jti: UUID) -> str:
        return f"blacklist:jti:{jti}"

    async def revoke(self, jti: UUID, user_id: UUID, exp: int, reason: str) -> bool:
        now = int(current_datetime().timestamp())
        ttl = exp - now
        if ttl <= 0:
            return False

        ttl = timedelta(seconds=ttl)
        key = self._build_key(jti)
        value = json.dumps({"revoked_at": now, "author_id": f"{user_id}", "reason": reason})
        await self.redis_client.setex(key, ttl, value)
        return True

    async def is_revoked(self, jti: UUID) -> bool:
        key = self._build_key(jti)
        is_exists = await self.redis_client.exists(key)
        return bool(is_exists)
