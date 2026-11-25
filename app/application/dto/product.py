from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.entities.product import Product


@dataclass(frozen=True, slots=True)
class CreateProductCommand:
    name: str
    sku: str
    price: Decimal
    stock: int = 0
    description: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateProductCommand:
    name: str | None = None
    price: Decimal | None = None
    stock: int | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ProductDTO:
    id: UUID
    name: str
    sku: str
    price: Decimal
    stock: int
    description: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, p: Product) -> "ProductDTO":
        return cls(
            id=p.id,
            name=p.name,
            sku=p.sku,
            price=p.price,
            stock=p.stock,
            description=p.description,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )

    # JSON-safe (de)serialisation used for the cache representation.
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "sku": self.sku,
            "price": str(self.price),
            "stock": self.stock,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProductDTO":
        return cls(
            id=UUID(d["id"]),
            name=d["name"],
            sku=d["sku"],
            price=Decimal(d["price"]),
            stock=d["stock"],
            description=d["description"],
            created_at=datetime.fromisoformat(d["created_at"]),
            updated_at=datetime.fromisoformat(d["updated_at"]),
        )


@dataclass(frozen=True, slots=True)
class ProductPage:
    items: list[ProductDTO]
    total: int
    offset: int
    limit: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "total": self.total,
            "offset": self.offset,
            "limit": self.limit,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProductPage":
        return cls(
            items=[ProductDTO.from_dict(i) for i in d["items"]],
            total=d["total"],
            offset=d["offset"],
            limit=d["limit"],
        )
