from fastapi import APIRouter

from app.presentation.api.v1 import health, products

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(products.router)

health_router = health.router
