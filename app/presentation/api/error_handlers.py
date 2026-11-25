from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import ConflictError, DomainError, EntityNotFoundError, ValidationError


def register_error_handlers(app: FastAPI) -> None:
    """Translate domain errors into HTTP responses (domain stays HTTP-agnostic)."""

    def _resp(code: int, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    @app.exception_handler(EntityNotFoundError)
    async def _not_found(_: Request, exc: EntityNotFoundError) -> JSONResponse:
        return _resp(status.HTTP_404_NOT_FOUND, exc)

    @app.exception_handler(ConflictError)
    async def _conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return _resp(status.HTTP_409_CONFLICT, exc)

    @app.exception_handler(ValidationError)
    async def _invalid(_: Request, exc: ValidationError) -> JSONResponse:
        return _resp(status.HTTP_422_UNPROCESSABLE_CONTENT, exc)

    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        return _resp(status.HTTP_400_BAD_REQUEST, exc)
