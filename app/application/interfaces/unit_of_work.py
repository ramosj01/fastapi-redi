from types import TracebackType
from typing import Protocol, Self

from app.domain.repositories.product_repository import ProductRepository


class UnitOfWork(Protocol):
    """Transaction boundary. Use cases commit explicitly; leaving the block rolls back."""

    products: ProductRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
