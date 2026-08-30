from datetime import UTC, datetime, timedelta

import jwt

from users_service.application.common.errors import AuthenticationError
from users_service.application.common.interfaces.security.i_token_service import (
    ITokenService,
)
from users_service.application.common.interfaces.security.tokens import (
    IssuedToken,
    TokenPayload,
)
from users_service.entities.user.value_objects import UserId


class JwtTokenService(ITokenService):
    """Signs and verifies stateless JWT access/refresh tokens (HMAC).

    Each token carries the subject (user id), a ``jti`` that ties it to a
    server-side session row, a ``type`` (``access``/``refresh``) and an expiry.
    The signature guarantees the payload was not tampered with; the ``jti`` is
    what makes revocation possible despite JWTs being self-contained.
    """

    _ACCESS = "access"
    _REFRESH = "refresh"

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_expire_minutes: int = 15,
        refresh_expire_minutes: int = 60 * 24 * 7,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_expire_minutes = access_expire_minutes
        self._refresh_expire_minutes = refresh_expire_minutes

    def issue_access(self, user_id: UserId, jti: str) -> IssuedToken:
        return self._issue(user_id, jti, self._ACCESS, self._access_expire_minutes)

    def issue_refresh(self, user_id: UserId, jti: str) -> IssuedToken:
        return self._issue(user_id, jti, self._REFRESH, self._refresh_expire_minutes)

    def decode(self, token: str) -> TokenPayload:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Invalid token") from exc

        try:
            user_id = UserId(int(claims["sub"]))
            jti = str(claims["jti"])
            token_type = str(claims["type"])
            expires_at = datetime.fromtimestamp(int(claims["exp"]), tz=UTC)
        except (KeyError, ValueError) as exc:
            raise AuthenticationError("Malformed token payload") from exc

        return TokenPayload(
            user_id=user_id,
            jti=jti,
            token_type=token_type,
            expires_at=expires_at,
        )

    def _issue(
        self, user_id: UserId, jti: str, token_type: str, minutes: int
    ) -> IssuedToken:
        expires_at = datetime.now(UTC) + timedelta(minutes=minutes)
        payload = {
            "sub": str(int(user_id)),
            "jti": jti,
            "type": token_type,
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return IssuedToken(token=token, jti=jti, expires_at=expires_at)
