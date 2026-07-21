from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from auth_test.application.common.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    EntityNotFoundError,
    ValidationError,
)


async def _authentication_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def _authorization_handler(
    request: Request, exc: AuthorizationError
) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


async def _not_found_handler(
    request: Request, exc: EntityNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def _conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def _validation_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def map_exc_handlers(app: FastAPI, /) -> None:
    """Translate application-layer errors into HTTP status codes."""
    app.add_exception_handler(AuthenticationError, _authentication_handler)
    app.add_exception_handler(AuthorizationError, _authorization_handler)
    app.add_exception_handler(EntityNotFoundError, _not_found_handler)
    app.add_exception_handler(ConflictError, _conflict_handler)
    app.add_exception_handler(ValidationError, _validation_handler)
