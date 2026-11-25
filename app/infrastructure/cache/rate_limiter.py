import logging
import time

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.application.interfaces.rate_limiter import RateLimitResult

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """Fixed-window limiter shared by all replicas (the counter lives in Redis)."""

    def __init__(self, redis: Redis, *, prefix: str, limit: int, window_seconds: int) -> None:
        self._redis = redis
        self._prefix = prefix
        self._limit = limit
        self._window = window_seconds

    async def hit(self, identity: str) -> RateLimitResult:
        now = int(time.time())
        window = now // self._window
        reset_after = self._window - (now % self._window)
        key = f"{self._prefix}:ratelimit:{identity}:{window}"
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, self._window + 1)
                count, _ = await pipe.execute()
        except RedisError:
            # Fail open: an unavailable limiter must not take the API down.
            logger.warning("rate limiter unavailable; allowing request", exc_info=True)
            return RateLimitResult(True, self._limit, self._limit, reset_after)

        remaining = max(self._limit - int(count), 0)
        return RateLimitResult(int(count) <= self._limit, self._limit, remaining, reset_after)
