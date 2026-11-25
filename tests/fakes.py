from types import TracebackType
from typing import Self
from uuid import UUID

from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository


class InMemoryProductRepository(ProductRepository):
    def __init__(self, store: dict[UUID, Product]) -> None:
        self.store = store
        self.reads = 0

    async def get(self, product_id: UUID) -> Product | None:
        self.reads += 1
        return self.store.get(product_id)

    async def get_by_sku(self, sku: str) -> Product | None:
        return next((p for p in self.store.values() if p.sku == sku), None)

    async def list(self, *, offset: int, limit: int) -> list[Product]:
        self.reads += 1
        items = sorted(self.store.values(), key=lambda p: p.created_at)
        return items[offset : offset + limit]

    async def count(self) -> int:
        return len(self.store)

    async def add(self, product: Product) -> Product:
        self.store[product.id] = product
        return product

    async def update(self, product: Product) -> Product:
        self.store[product.id] = product
        return product

    async def delete(self, product_id: UUID) -> bool:
        return self.store.pop(product_id, None) is not None


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.committed: dict[UUID, Product] = {}
        self.products = InMemoryProductRepository(dict(self.committed))
        self.commits = 0

    async def __aenter__(self) -> Self:
        self.products.store = dict(self.committed)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.products.store = dict(self.committed)  # discard uncommitted

    async def commit(self) -> None:
        self.committed = dict(self.products.store)
        self.commits += 1

    async def rollback(self) -> None:
        self.products.store = dict(self.committed)
