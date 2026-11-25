import logging
from uuid import UUID

from app.application.dto.product import (
    CreateProductCommand,
    ProductDTO,
    ProductPage,
    UpdateProductCommand,
)
from app.application.interfaces.cache import CacheService
from app.application.interfaces.unit_of_work import UnitOfWork
from app.domain.entities.product import Product
from app.domain.exceptions import ConflictError, EntityNotFoundError

logger = logging.getLogger(__name__)

LIST_NAMESPACE = "products:list"


def product_key(product_id: UUID) -> str:
    return f"products:item:{product_id}"


class ProductService:
    """Product use cases. Depends only on ports, never on Redis/SQLAlchemy/FastAPI."""

    def __init__(self, uow: UnitOfWork, cache: CacheService, cache_ttl: int) -> None:
        self._uow = uow
        self._cache = cache
        self._ttl = cache_ttl

    # ---------- queries (cache-aside) ----------

    async def get_product(self, product_id: UUID) -> ProductDTO:
        async def load() -> dict | None:
            async with self._uow as uow:
                product = await uow.products.get(product_id)
                return ProductDTO.from_entity(product).to_dict() if product else None

        data = await self._cache.get_or_set(product_key(product_id), load, self._ttl)
        if data is None:
            raise EntityNotFoundError("Product", product_id)
        return ProductDTO.from_dict(data)

    async def list_products(self, *, offset: int, limit: int) -> ProductPage:
        version = await self._cache.get_version(LIST_NAMESPACE)
        key = f"{LIST_NAMESPACE}:v{version}:{offset}:{limit}"

        async def load() -> dict:
            async with self._uow as uow:
                items = await uow.products.list(offset=offset, limit=limit)
                total = await uow.products.count()
            return ProductPage(
                items=[ProductDTO.from_entity(p) for p in items],
                total=total,
                offset=offset,
                limit=limit,
            ).to_dict()

        data = await self._cache.get_or_set(key, load, self._ttl)
        return ProductPage.from_dict(data)

    # ---------- commands (write to DB, then invalidate shared cache) ----------

    async def create_product(self, cmd: CreateProductCommand) -> ProductDTO:
        async with self._uow as uow:
            if await uow.products.get_by_sku(cmd.sku):
                raise ConflictError(f"Product with SKU '{cmd.sku}' already exists")
            product = Product(
                name=cmd.name,
                sku=cmd.sku,
                price=cmd.price,
                stock=cmd.stock,
                description=cmd.description,
            )
            await uow.products.add(product)
            await uow.commit()

        dto = ProductDTO.from_entity(product)
        await self._invalidate_lists()
        await self._cache.set(product_key(product.id), dto.to_dict(), self._ttl)
        return dto

    async def update_product(self, product_id: UUID, cmd: UpdateProductCommand) -> ProductDTO:
        async with self._uow as uow:
            product = await uow.products.get(product_id)
            if product is None:
                raise EntityNotFoundError("Product", product_id)
            product.update(
                name=cmd.name, price=cmd.price, stock=cmd.stock, description=cmd.description
            )
            await uow.products.update(product)
            await uow.commit()

        # Delete rather than overwrite: avoids racing replicas writing stale values.
        await self._cache.delete(product_key(product_id))
        await self._invalidate_lists()
        return ProductDTO.from_entity(product)

    async def delete_product(self, product_id: UUID) -> None:
        async with self._uow as uow:
            if not await uow.products.delete(product_id):
                raise EntityNotFoundError("Product", product_id)
            await uow.commit()

        await self._cache.delete(product_key(product_id))
        await self._invalidate_lists()

    async def _invalidate_lists(self) -> None:
        await self._cache.bump_version(LIST_NAMESPACE)
