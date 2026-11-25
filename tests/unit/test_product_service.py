from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.dto.product import CreateProductCommand, UpdateProductCommand
from app.application.services.product_service import ProductService
from app.domain.exceptions import ConflictError, EntityNotFoundError
from tests.fakes import InMemoryUnitOfWork


@pytest.fixture
def uow():
    return InMemoryUnitOfWork()


@pytest.fixture
def service(uow, cache):
    return ProductService(uow, cache, cache_ttl=60)


async def _create(service, sku="SKU-1"):
    return await service.create_product(
        CreateProductCommand(name="Widget", sku=sku, price=Decimal("9.99"), stock=3)
    )


async def test_get_is_served_from_cache_after_first_read(service, uow):
    created = await _create(service)
    # Created item is written through to the cache, so the DB isn't touched.
    reads_before = uow.products.reads
    got = await service.get_product(created.id)
    assert got == created
    assert uow.products.reads == reads_before


async def test_update_invalidates_item_and_list(service):
    created = await _create(service)
    page = await service.list_products(offset=0, limit=10)
    assert page.items[0].stock == 3

    await service.update_product(created.id, UpdateProductCommand(stock=10))

    assert (await service.get_product(created.id)).stock == 10
    assert (await service.list_products(offset=0, limit=10)).items[0].stock == 10


async def test_delete_invalidates(service):
    created = await _create(service)
    await service.get_product(created.id)
    await service.delete_product(created.id)
    with pytest.raises(EntityNotFoundError):
        await service.get_product(created.id)
    assert (await service.list_products(offset=0, limit=10)).total == 0


async def test_duplicate_sku_conflicts(service):
    await _create(service)
    with pytest.raises(ConflictError):
        await _create(service)


async def test_missing_product_raises(service):
    with pytest.raises(EntityNotFoundError):
        await service.get_product(uuid4())
