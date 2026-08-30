"""Browser-side session storage: HttpOnly cookies instead of ``localStorage``.

For a normal web frontend this is the safer half of the JWT story. The access
and refresh tokens are set as **HttpOnly** cookies, so no script on the page —
including an injected one — can read them; the browser attaches them on its
own. Because the browser now sends credentials automatically, state-changing
requests are additionally verified with a double-submit CSRF token: a *readable*
cookie the frontend copies into a request header (see :mod:`csrf_middleware`).

The visitor cookie is a different thing entirely: not a credential, just a
long-lived opaque browser id that lets the analytics side ask "what did this
visitor do?" and, after a signup, tie that history to an account.
"""

import secrets
from datetime import UTC, datetime

from fastapi import Request, Response

from users_service.application.common.dto import AuthTokenDTO
from users_service.infrastructure.config import Config


class SessionCookies:
    """Reads and writes the auth, CSRF and visitor cookies."""

    def __init__(self, config: Config) -> None:
        self._config = config

    # --- reading ----------------------------------------------------------

    def read_access_token(self, request: Request) -> str | None:
        return request.cookies.get(self._config.ACCESS_COOKIE_NAME)

    def read_refresh_token(self, request: Request) -> str | None:
        return request.cookies.get(self._config.REFRESH_COOKIE_NAME)

    # --- writing ----------------------------------------------------------

    def set_tokens(self, response: Response, tokens: AuthTokenDTO) -> str | None:
        """Store the token pair in cookies; return the new CSRF token.

        Each cookie expires with the token it carries, so a browser stops
        sending credentials the server would reject anyway.
        """
        self._set(
            response,
            self._config.ACCESS_COOKIE_NAME,
            tokens.access_token,
            path="/",
            max_age=self._max_age(tokens.access_expires_at),
            httponly=True,
        )
        self._set(
            response,
            self._config.REFRESH_COOKIE_NAME,
            tokens.refresh_token,
            path=self._config.REFRESH_COOKIE_PATH,
            max_age=self._max_age(tokens.refresh_expires_at),
            httponly=True,
        )

        if not self._config.CSRF_PROTECTION:
            return None

        csrf_token = secrets.token_urlsafe(32)
        self._set(
            response,
            self._config.CSRF_COOKIE_NAME,
            csrf_token,
            path="/",
            max_age=self._max_age(tokens.refresh_expires_at),
            httponly=False,  # the frontend must read it to echo it back
        )
        return csrf_token

    def clear_tokens(self, response: Response) -> None:
        """Drop the auth cookies (logout / account deletion)."""
        for name, path in (
            (self._config.ACCESS_COOKIE_NAME, "/"),
            (self._config.REFRESH_COOKIE_NAME, self._config.REFRESH_COOKIE_PATH),
            (self._config.CSRF_COOKIE_NAME, "/"),
        ):
            response.delete_cookie(
                name,
                path=path,
                domain=self._config.COOKIE_DOMAIN,
                secure=self._config.COOKIE_SECURE,
                samesite=self._config.COOKIE_SAMESITE,
            )

    # --- internals --------------------------------------------------------

    def _set(
        self,
        response: Response,
        name: str,
        value: str,
        *,
        path: str,
        max_age: int,
        httponly: bool,
    ) -> None:
        response.set_cookie(
            name,
            value,
            max_age=max_age,
            path=path,
            domain=self._config.COOKIE_DOMAIN,
            secure=self._config.COOKIE_SECURE,
            httponly=httponly,
            samesite=self._config.COOKIE_SAMESITE,
        )

    @staticmethod
    def _max_age(expires_at: datetime) -> int:
        moment = expires_at
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        return max(int((moment - datetime.now(UTC)).total_seconds()), 0)
