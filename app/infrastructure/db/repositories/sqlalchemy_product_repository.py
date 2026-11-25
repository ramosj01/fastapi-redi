from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.db.models import ProductModel


def _to_entity(m: ProductModel) -> Product:
    return Product(
        id=m.id,
        name=m.name,
        sku=m.sku,
        price=m.price,
        stock=m.stock,
        description=m.description,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlAlchemyProductRepository(ProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, product_id: UUID) -> Product | None:
        m = await self._session.get(ProductModel, product_id)
        return _to_entity(m) if m else None

    async def get_by_sku(self, sku: str) -> Product | None:
        m = await self._session.scalar(select(ProductModel).where(ProductModel.sku == sku))
        return _to_entity(m) if m else None

    async def list(self, *, offset: int, limit: int) -> list[Product]:
        rows = await self._session.scalars(
            select(ProductModel)
            .order_by(ProductModel.created_at, ProductModel.id)
            .offset(offset)
            .limit(limit)
        )
        return [_to_entity(m) for m in rows]

    async def count(self) -> int:
        return int(await self._session.scalar(select(func.count()).select_from(ProductModel)))

    async def add(self, product: Product) -> Product:
        self._session.add(
            ProductModel(
                id=product.id,
                name=product.name,
                sku=product.sku,
                price=product.price,
                stock=product.stock,
                description=product.description,
                created_at=product.created_at,
                updated_at=product.updated_at,
            )
        )
        await self._session.flush()
        return product

    async def update(self, product: Product) -> Product:
        m = await self._session.get(ProductModel, product.id)
        if m is None:
            raise LookupError(product.id)
        m.name = product.name
        m.price = product.price
        m.stock = product.stock
        m.description = product.description
        m.updated_at = product.updated_at
        await self._session.flush()
        return product

    async def delete(self, product_id: UUID) -> bool:
        result = await self._session.execute(
            delete(ProductModel).where(ProductModel.id == product_id)
        )
        return result.rowcount > 0
