import asyncio

from redis.exceptions import ConnectionError as RedisConnectionError

from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.cache.redis_lock import RedisLock


async def test_stampede_protection_calls_loader_once(redis):
    # Two caches on the same Redis simulate two replicas.
    replicas = [
        RedisCache(redis, prefix="t", default_ttl=60, lock_wait=2, poll_interval=0.01)
        for _ in range(2)
    ]
    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.1)
        return {"v": 1}

    results = await asyncio.gather(*(replicas[i % 2].get_or_set("hot", loader) for i in range(20)))
    assert calls == 1
    assert all(r == {"v": 1} for r in results)


async def test_negative_caching(cache):
    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        return None

    assert await cache.get_or_set("missing", loader) is None
    assert await cache.get_or_set("missing", loader) is None
    assert calls == 1


async def test_version_bump(cache):
    assert await cache.get_version("ns") == 0
    assert await cache.bump_version("ns") == 1
    assert await cache.get_version("ns") == 1


class _BrokenRedis:
    def __getattr__(self, name):
        async def fail(*a, **kw):
            raise RedisConnectionError("down")

        return fail


async def test_degrades_when_redis_is_down():
    cache = RedisCache(_BrokenRedis(), prefix="t", default_ttl=60)  # type: ignore[arg-type]

    async def loader():
        return {"ok": True}

    assert await cache.get_or_set("k", loader) == {"ok": True}
    assert await cache.get("k") is None
    await cache.set("k", 1)
    await cache.delete("k")


async def test_lock_is_exclusive_and_owner_safe(redis):
    a = RedisLock(redis, "L", timeout=5, wait=0)
    b = RedisLock(redis, "L", timeout=5, wait=0)
    assert await a.acquire()
    assert not await b.acquire()
    await b.release()  # non-owner release is a no-op
    assert await redis.exists("L")
    await a.release()
    assert await b.acquire()
