from users_service.application.auth.interfaces.i_authenticate_usecase import (
    IAuthenticateUseCase,
)
from users_service.application.common import user_cache_codec
from users_service.application.common.errors import AuthenticationError
from users_service.application.common.interfaces.i_cache import ICache
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_token_service import (
    ITokenService,
)
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import UserId


class AuthenticateUseCase(IAuthenticateUseCase):
    """Resolve the logged-in user behind a request's access token.

    This is the gate every protected endpoint passes through. It fails (401)
    unless the token is a well-signed, unexpired *access* token, its session is
    still valid (not revoked), and the user is still active.

    The session is always checked against the database, so logout / soft-delete
    revoke access immediately. The *user* (with roles + permissions) may be
    served from the cache to avoid a join on every request; that cache is
    short-lived and is invalidated when a user's roles or profile change.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        token_service: ITokenService,
        cache: ICache,
        cache_ttl_seconds: int,
    ) -> None:
        self._uow = uow
        self._token_service = token_service
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    async def __call__(self, token: str) -> User:
        payload = self._token_service.decode(token)

        if payload.token_type != "access":
            raise AuthenticationError("An access token is required")

        async with self._uow as uow:
            session = await uow.sessions.get_by_jti(payload.jti)
            if session is None or not session.is_valid():
                raise AuthenticationError("Session is no longer valid")

            user = await self._load_user(uow, payload.user_id)
            if user is None or not user.is_active:
                raise AuthenticationError("User is inactive or missing")

            return user

    async def _load_user(self, uow: IUnitOfWork, user_id: UserId) -> User | None:
        key = user_cache_codec.user_cache_key(user_id)

        cached = await self._cache.get(key)
        if cached is not None:
            return user_cache_codec.loads(cached)

        user = await uow.users.get_by_id(user_id)
        if user is not None:
            await self._cache.set(
                key, user_cache_codec.dumps(user), self._cache_ttl_seconds
            )
        return user
