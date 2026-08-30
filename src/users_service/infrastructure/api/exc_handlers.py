from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from users_service.application.common.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    EntityNotFoundError,
    InvalidTokenError,
    RateLimitedError,
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


async def _rate_limited_handler(
    request: Request, exc: RateLimitedError
) -> JSONResponse:
    """429 with a ``Retry-After`` header, so a client can back off correctly."""
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


async def _invalid_token_handler(
    request: Request, exc: InvalidTokenError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def _validation_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def map_exc_handlers(app: FastAPI, /) -> None:
    """Translate application-layer errors into HTTP status codes.

    Starlette resolves a handler by walking the exception's class hierarchy,
    so the more specific entries (a spent link, a rate limit) win over the
    general ones they inherit from.
    """
    app.add_exception_handler(AuthenticationError, _authentication_handler)
    app.add_exception_handler(AuthorizationError, _authorization_handler)
    app.add_exception_handler(EntityNotFoundError, _not_found_handler)
    app.add_exception_handler(ConflictError, _conflict_handler)
    app.add_exception_handler(RateLimitedError, _rate_limited_handler)
    app.add_exception_handler(InvalidTokenError, _invalid_token_handler)
    app.add_exception_handler(ValidationError, _validation_handler)
