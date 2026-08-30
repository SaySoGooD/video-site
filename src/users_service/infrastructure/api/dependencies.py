"""FastAPI dependencies that enforce authentication and authorization.

``get_current_user`` answers "who is calling?" (401 if it cannot tell).
``require_permission`` answers "are they allowed?" (403 if not). Both read the
DI container from ``app.state`` so they work without module wiring, including
the parameterized permission factory.

Credentials are accepted from two places: the HttpOnly cookie a browser sends
by itself, and an ``Authorization: Bearer`` header for non-browser callers
(mobile apps, other services). The cookie wins when both are present.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from users_service.application.common.dto import DeviceInfoDTO
from users_service.application.common.errors import (
    AuthenticationError,
    AuthorizationError,
)
from users_service.entities.user.models import User
from users_service.infrastructure.api.cookies import SessionCookies
from users_service.infrastructure.config import Config

_bearer_scheme = HTTPBearer(auto_error=False)


def get_config(request: Request) -> Config:
    return request.app.state.container.config()


def get_cookies(request: Request) -> SessionCookies:
    return SessionCookies(get_config(request))


def get_visitor_id(request: Request) -> str | None:
    """Return this browser's visitor id.

    ``VisitorMiddleware`` has already read or minted it, so every request —
    anonymous ones included — carries one by the time a handler runs.
    """
    return getattr(request.state, "visitor_id", None)


def get_device_info(
    request: Request,
    visitor_id: str | None = Depends(get_visitor_id),
    config: Config = Depends(get_config),
) -> DeviceInfoDTO:
    """Describe the caller's device for the session record."""
    return DeviceInfoDTO(
        visitor_id=visitor_id,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request, config),
    )


def get_access_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    cookies: SessionCookies = Depends(get_cookies),
    config: Config = Depends(get_config),
) -> str:
    """Extract the access token from the cookie or the bearer header."""
    if config.COOKIE_AUTH_ENABLED:
        from_cookie = cookies.read_access_token(request)
        if from_cookie:
            return from_cookie

    if credentials is not None and credentials.credentials:
        return credentials.credentials

    raise AuthenticationError("Missing access token")


async def get_current_user(
    request: Request,
    token: str = Depends(get_access_token),
) -> User:
    """Resolve the logged-in user behind the request's access token."""
    usecase = request.app.state.container.authenticate_usecase()
    return await usecase(token)


def get_current_jti(
    request: Request,
    token: str = Depends(get_access_token),
) -> str:
    """Return the session id (``jti``) the request is authenticated with.

    Used to mark "this is the device you are on" in the session list. The token
    has already been validated by :func:`get_current_user`; decoding it again
    is a signature check, not another database round trip.
    """
    return request.app.state.container.token_service().decode(token).jti


def require_permission(
    resource: str, action: str
) -> Callable[[User], Awaitable[User]]:
    """Build a dependency that enforces one ``resource:action`` permission.

    Delegates the actual decision to the domain (``User.has_permission``), so
    superusers pass automatically and role/permission changes take effect
    without touching the endpoints.
    """

    async def checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(resource, action):
            raise AuthorizationError(
                f"Missing required permission: {resource}:{action}"
            )
        return user

    return checker


def _client_ip(request: Request, config: Config) -> str | None:
    """Best-effort caller address.

    ``X-Forwarded-For`` is only trusted when the deployment says a proxy sets
    it; otherwise any client could dictate the address stored on its session.
    """
    if config.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client is not None else None
