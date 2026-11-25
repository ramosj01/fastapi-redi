from decimal import Decimal

import pytest

from app.domain.entities.product import Product
from app.domain.exceptions import ValidationError


def test_rejects_negative_price():
    with pytest.raises(ValidationError):
        Product(name="x", sku="s", price=Decimal("-1"))


def test_update_validates_and_touches_timestamp():
    p = Product(name="x", sku="s", price=Decimal("1"))
    before = p.updated_at
    p.update(stock=5)
    assert p.stock == 5 and p.updated_at >= before
    with pytest.raises(ValidationError):
        p.update(name="  ")
