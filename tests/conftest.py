import fakeredis
import pytest

from app.infrastructure.cache.redis_cache import RedisCache


@pytest.fixture
def redis_server() -> fakeredis.FakeServer:
    return fakeredis.FakeServer()


@pytest.fixture
def redis(redis_server):
    return fakeredis.FakeAsyncRedis(server=redis_server, decode_responses=True)


@pytest.fixture
def cache(redis) -> RedisCache:
    return RedisCache(redis, prefix="test", default_ttl=60, lock_wait=1.0, poll_interval=0.01)
