from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.application.dto.product import CreateProductCommand, UpdateProductCommand
from app.presentation.api.dependencies import ProductServiceDep, rate_limit
from app.presentation.api.schemas.product import (
    ProductCreate,
    ProductOut,
    ProductPageOut,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["products"], dependencies=[Depends(rate_limit)])


@router.get("", response_model=ProductPageOut)
async def list_products(
    service: ProductServiceDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return await service.list_products(offset=offset, limit=limit)


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, service: ProductServiceDep):
    return await service.get_product(product_id)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(body: ProductCreate, service: ProductServiceDep):
    return await service.create_product(CreateProductCommand(**body.model_dump()))


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(product_id: UUID, body: ProductUpdate, service: ProductServiceDep):
    return await service.update_product(
        product_id, UpdateProductCommand(**body.model_dump(exclude_unset=True))
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: UUID, service: ProductServiceDep) -> None:
    await service.delete_product(product_id)
