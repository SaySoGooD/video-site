from abc import ABC, abstractmethod

from auth_test.application.common.interfaces.security.tokens import (
    IssuedToken,
    TokenPayload,
)
from auth_test.entities.user.value_objects import UserId


class ITokenService(ABC):
    """Port for encoding and decoding stateless access/refresh tokens (JWT).

    Both token kinds carry the same ``jti`` so they map to one server-side
    session and can be revoked together. The caller supplies the ``jti`` so it
    controls the link between the tokens and the session row.
    """

    @abstractmethod
    def issue_access(self, user_id: UserId, jti: str) -> IssuedToken:
        """Create a short-lived access token of type ``access``."""
        ...

    @abstractmethod
    def issue_refresh(self, user_id: UserId, jti: str) -> IssuedToken:
        """Create a long-lived refresh token of type ``refresh``."""
        ...

    @abstractmethod
    def decode(self, token: str) -> TokenPayload:
        """Verify the signature/expiry and return the payload.

        Raises :class:`AuthenticationError` if the token is invalid.
        """
        ...
