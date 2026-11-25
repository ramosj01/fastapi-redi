from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.exceptions import ValidationError


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Product:
    """Pure domain entity: no framework, ORM or cache knowledge."""

    name: str
    sku: str
    price: Decimal
    stock: int = 0
    description: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("Product name must not be empty")
        if not self.sku or not self.sku.strip():
            raise ValidationError("Product SKU must not be empty")
        if self.price < 0:
            raise ValidationError("Product price must be non-negative")
        if self.stock < 0:
            raise ValidationError("Product stock must be non-negative")

    def update(
        self,
        *,
        name: str | None = None,
        price: Decimal | None = None,
        stock: int | None = None,
        description: str | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        if price is not None:
            self.price = price
        if stock is not None:
            self.stock = stock
        if description is not None:
            self.description = description
        self._validate()
        self.updated_at = _now()
