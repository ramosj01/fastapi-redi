import asyncio
import time
import uuid
from typing import Self

from redis.asyncio import Redis

from app.application.interfaces.lock import LockNotAcquiredError

# Only the owner (matching token) may release; prevents deleting a lock that
# expired and was re-acquired by another replica.
_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


class RedisLock:
    """Single-instance Redis lock (SET NX PX + token-checked release)."""

    def __init__(
        self,
        redis: Redis,
        name: str,
        *,
        timeout: float = 5.0,
        wait: float = 2.0,
        poll_interval: float = 0.05,
    ) -> None:
        self._redis = redis
        self.name = name
        self._timeout_ms = int(timeout * 1000)
        self._wait = wait
        self._poll = poll_interval
        self._token: str | None = None

    async def acquire(self, blocking: bool = True) -> bool:
        token = uuid.uuid4().hex
        deadline = time.monotonic() + self._wait
        while True:
            if await self._redis.set(self.name, token, nx=True, px=self._timeout_ms):
                self._token = token
                return True
            if not blocking or time.monotonic() >= deadline:
                return False
            await asyncio.sleep(self._poll)

    async def release(self) -> None:
        if self._token is None:
            return
        try:
            await self._redis.eval(_RELEASE_SCRIPT, 1, self.name, self._token)
        finally:
            self._token = None

    async def __aenter__(self) -> Self:
        if not await self.acquire():
            raise LockNotAcquiredError(self.name)
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.release()
