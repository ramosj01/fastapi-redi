from typing import Protocol, Self


class LockNotAcquiredError(Exception):
    pass


class DistributedLock(Protocol):
    """Mutual exclusion that holds across every replica of the service."""

    async def acquire(self, blocking: bool = True) -> bool: ...

    async def release(self) -> None: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *exc: object) -> None: ...
