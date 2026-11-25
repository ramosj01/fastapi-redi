"""Composition root: the only place that knows about concrete implementations."""

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.application.services.product_service import ProductService
from app.core.config import Settings
from app.infrastructure.cache.rate_limiter import RedisRateLimiter
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.cache.redis_client import create_redis
from app.infrastructure.cache.redis_lock import RedisLock
from app.infrastructure.db.session import create_engine, create_session_factory
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


class Container:
    def __init__(
        self,
        settings: Settings,
        *,
        redis: Redis | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        self.settings = settings
        self.redis = redis or create_redis(settings.redis_url, settings.redis_max_connections)
        self.engine = engine or create_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = create_session_factory(self.engine)
        self.cache = RedisCache(
            self.redis,
            prefix=settings.cache_key_prefix,
            default_ttl=settings.cache_default_ttl_seconds,
            lock_timeout=settings.cache_lock_timeout_seconds,
            lock_wait=settings.cache_lock_wait_seconds,
        )
        self.rate_limiter = RedisRateLimiter(
            self.redis,
            prefix=settings.cache_key_prefix,
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )

    # ----- factories (per request) -----

    def unit_of_work(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)

    def product_service(self) -> ProductService:
        return ProductService(
            self.unit_of_work(), self.cache, self.settings.cache_default_ttl_seconds
        )

    def lock(self, name: str, *, timeout: float = 10.0, wait: float = 5.0) -> RedisLock:
        return RedisLock(
            self.redis, f"{self.settings.cache_key_prefix}:lock:{name}", timeout=timeout, wait=wait
        )

    # ----- health -----

    async def check_redis(self) -> bool:
        try:
            return bool(await self.redis.ping())
        except Exception:
            return False

    async def check_database(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def shutdown(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()
