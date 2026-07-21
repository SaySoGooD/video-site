"""FastAPI dependencies that enforce authentication and authorization.

``get_current_user`` answers "who is calling?" (401 if it cannot tell).
``require_permission`` answers "are they allowed?" (403 if not). Both read the
DI container from ``app.state`` so they work without module wiring, including
the parameterized permission factory.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth_test.application.common.errors import (
    AuthenticationError,
    AuthorizationError,
)
from auth_test.entities.user.models import User

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    """Resolve the logged-in user from the ``Authorization: Bearer`` header."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Missing bearer token")

    usecase = request.app.state.container.authenticate_usecase()
    return await usecase(credentials.credentials)


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
