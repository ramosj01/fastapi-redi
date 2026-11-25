from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status

from app.application.services.product_service import ProductService
from app.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_product_service(container: ContainerDep) -> ProductService:
    return container.product_service()


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


def _client_identity(request: Request) -> str:
    # Behind a load balancer the real client is the first X-Forwarded-For hop.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request, response: Response, container: ContainerDep) -> None:
    if not container.settings.rate_limit_enabled:
        return
    result = await container.rate_limiter.hit(_client_identity(request))
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_after),
    }
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={**headers, "Retry-After": str(result.reset_after)},
        )
    response.headers.update(headers)
