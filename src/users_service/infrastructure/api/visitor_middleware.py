"""Issues the long-lived ``visitor_id`` cookie to every browser that arrives.

It runs as middleware rather than as a route dependency so the id is handed out
on *every* response — including 401s, 404s and error responses produced by an
exception handler, which never pass back through a dependency. A visitor whose
first click is a failed login is still the same visitor afterwards.

The id identifies a browser, not a person, and is not a credential: nothing is
ever authorized on the strength of it.
"""

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from users_service.infrastructure.config import Config


class VisitorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, config: Config) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._config = config

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        visitor_id = request.cookies.get(self._config.VISITOR_COOKIE_NAME)
        is_new = not visitor_id
        if is_new:
            visitor_id = str(uuid.uuid4())

        # Handlers read it from here, so they see the freshly minted id on the
        # very request that creates it (a signup, typically).
        request.state.visitor_id = visitor_id

        response = await call_next(request)

        if is_new and visitor_id is not None:
            response.set_cookie(
                self._config.VISITOR_COOKIE_NAME,
                visitor_id,
                max_age=self._config.VISITOR_COOKIE_MAX_AGE_DAYS * 24 * 60 * 60,
                path="/",
                domain=self._config.COOKIE_DOMAIN,
                secure=self._config.COOKIE_SECURE,
                httponly=True,
                samesite=self._config.COOKIE_SAMESITE,
            )
        return response
