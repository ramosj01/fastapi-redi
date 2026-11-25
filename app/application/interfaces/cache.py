from collections.abc import Awaitable, Callable
from typing import Any, Protocol

JSONValue = Any
Loader = Callable[[], Awaitable[JSONValue | None]]


class CacheService(Protocol):
    """Port for a shared (cross-replica) cache. Values must be JSON-serialisable."""

    async def get(self, key: str) -> JSONValue | None: ...

    async def set(self, key: str, value: JSONValue, ttl: int | None = None) -> None: ...

    async def delete(self, *keys: str) -> None: ...

    async def get_version(self, namespace: str) -> int:
        """Current version of a key namespace (used for O(1) group invalidation)."""
        ...

    async def bump_version(self, namespace: str) -> int:
        """Invalidate every key built from the namespace's current version."""
        ...

    async def get_or_set(
        self, key: str, loader: Loader, ttl: int | None = None
    ) -> JSONValue | None:
        """Cache-aside read with stampede protection across all replicas."""
        ...
