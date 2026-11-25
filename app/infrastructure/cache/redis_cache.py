import asyncio
import json
import logging
import time
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.application.interfaces.cache import JSONValue, Loader
from app.infrastructure.cache.redis_lock import RedisLock

logger = logging.getLogger(__name__)

_MISS_MARKER = "__cache_miss__"


class RedisCache:
    """Shared cache adapter.

    * Keys are namespaced so several services can share one Redis.
    * ``get_or_set`` uses a distributed lock so that on a miss only ONE replica
      hits the database (cache-stampede protection); others wait for the value.
    * Misses are negatively cached for a short TTL (cache-penetration protection).
    * Redis outages degrade to direct loads instead of failing requests.
    """

    def __init__(
        self,
        redis: Redis,
        *,
        prefix: str,
        default_ttl: int,
        lock_timeout: float = 5.0,
        lock_wait: float = 2.0,
        negative_ttl: int = 10,
        poll_interval: float = 0.05,
    ) -> None:
        self._redis = redis
        self._prefix = prefix
        self._ttl = default_ttl
        self._lock_timeout = lock_timeout
        self._lock_wait = lock_wait
        self._negative_ttl = negative_ttl
        self._poll = poll_interval

    def _k(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def _get_raw(self, key: str) -> str | None:
        return await self._redis.get(self._k(key))

    @staticmethod
    def _decode(raw: str) -> Any:
        return json.loads(raw)

    async def get(self, key: str) -> JSONValue | None:
        try:
            raw = await self._get_raw(key)
        except RedisError:
            logger.warning("cache get failed", exc_info=True)
            return None
        if raw is None or raw == _MISS_MARKER:
            return None
        return self._decode(raw)

    async def set(self, key: str, value: JSONValue, ttl: int | None = None) -> None:
        try:
            await self._redis.set(self._k(key), json.dumps(value), ex=ttl or self._ttl)
        except RedisError:
            logger.warning("cache set failed", exc_info=True)

    async def delete(self, *keys: str) -> None:
        if not keys:
            return
        try:
            await self._redis.delete(*(self._k(k) for k in keys))
        except RedisError:
            logger.error("cache delete failed; entries may be stale until TTL", exc_info=True)

    async def get_version(self, namespace: str) -> int:
        try:
            v = await self._redis.get(self._k(f"{namespace}:version"))
        except RedisError:
            logger.warning("cache version read failed", exc_info=True)
            return 0
        return int(v) if v else 0

    async def bump_version(self, namespace: str) -> int:
        try:
            return int(await self._redis.incr(self._k(f"{namespace}:version")))
        except RedisError:
            logger.error("cache version bump failed", exc_info=True)
            return 0

    async def get_or_set(
        self, key: str, loader: Loader, ttl: int | None = None
    ) -> JSONValue | None:
        try:
            raw = await self._get_raw(key)
        except RedisError:
            logger.warning("cache unavailable, loading from source", exc_info=True)
            return await loader()

        if raw is not None:
            return None if raw == _MISS_MARKER else self._decode(raw)

        lock = RedisLock(self._redis, self._k(f"lock:{key}"), timeout=self._lock_timeout, wait=0)
        try:
            acquired = await lock.acquire(blocking=False)
        except RedisError:
            return await loader()

        if acquired:
            try:
                # Double-check: another replica may have filled it just before we locked.
                raw = await self._get_raw(key)
                if raw is not None:
                    return None if raw == _MISS_MARKER else self._decode(raw)
                value = await loader()
                await self._store(key, value, ttl)
                return value
            finally:
                try:
                    await lock.release()
                except RedisError:
                    logger.warning("lock release failed", exc_info=True)

        # Another replica is computing the value: wait for it, then fall back.
        deadline = time.monotonic() + self._lock_wait
        while time.monotonic() < deadline:
            await asyncio.sleep(self._poll)
            try:
                raw = await self._get_raw(key)
            except RedisError:
                break
            if raw is not None:
                return None if raw == _MISS_MARKER else self._decode(raw)
        return await loader()

    async def _store(self, key: str, value: JSONValue | None, ttl: int | None) -> None:
        try:
            if value is None:
                await self._redis.set(self._k(key), _MISS_MARKER, ex=self._negative_ttl)
            else:
                await self._redis.set(self._k(key), json.dumps(value), ex=ttl or self._ttl)
        except RedisError:
            logger.warning("cache store failed", exc_info=True)
