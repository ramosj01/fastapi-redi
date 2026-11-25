from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.product import Product


class ProductRepository(ABC):
    """Port for product persistence. Implemented in the infrastructure layer."""

    @abstractmethod
    async def get(self, product_id: UUID) -> Product | None: ...

    @abstractmethod
    async def get_by_sku(self, sku: str) -> Product | None: ...

    @abstractmethod
    async def list(self, *, offset: int, limit: int) -> list[Product]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def add(self, product: Product) -> Product: ...

    @abstractmethod
    async def update(self, product: Product) -> Product: ...

    @abstractmethod
    async def delete(self, product_id: UUID) -> bool: ...
