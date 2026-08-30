"""Double-submit CSRF check for cookie-authenticated requests.

With tokens in cookies the browser attaches credentials to *any* request it
makes, including one triggered by another site. The defence is that a foreign
page can make the browser send a cookie but cannot read one: on login the
service sets a readable ``csrf_token`` cookie, the frontend copies it into the
``X-CSRF-Token`` header, and a request whose header does not match its cookie is
rejected with 403.

Only unsafe methods are checked, and only when the request actually carries an
auth cookie — a first login has no cookies yet, and a service-to-service call
using ``Authorization: Bearer`` is not exposed to CSRF at all.
"""

import secrets

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from users_service.infrastructure.config import Config

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class CsrfMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, config: Config) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._config = config

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if self._requires_check(request) and not self._token_matches(request):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid"},
            )
        return await call_next(request)

    def _requires_check(self, request: Request) -> bool:
        if not (self._config.CSRF_PROTECTION and self._config.COOKIE_AUTH_ENABLED):
            return False
        if request.method in _SAFE_METHODS:
            return False
        return any(
            name in request.cookies
            for name in (
                self._config.ACCESS_COOKIE_NAME,
                self._config.REFRESH_COOKIE_NAME,
            )
        )

    def _token_matches(self, request: Request) -> bool:
        cookie = request.cookies.get(self._config.CSRF_COOKIE_NAME)
        header = request.headers.get(self._config.CSRF_HEADER_NAME)
        if not cookie or not header:
            return False
        return secrets.compare_digest(cookie, header)
