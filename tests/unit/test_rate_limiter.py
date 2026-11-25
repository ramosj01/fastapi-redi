from app.infrastructure.cache.rate_limiter import RedisRateLimiter


async def test_limit_is_shared_between_replicas(redis):
    r1 = RedisRateLimiter(redis, prefix="t", limit=3, window_seconds=60)
    r2 = RedisRateLimiter(redis, prefix="t", limit=3, window_seconds=60)
    results = [await (r1 if i % 2 else r2).hit("1.2.3.4") for i in range(4)]
    assert [r.allowed for r in results] == [True, True, True, False]
    assert results[2].remaining == 0
    assert (await r1.hit("5.6.7.8")).allowed
