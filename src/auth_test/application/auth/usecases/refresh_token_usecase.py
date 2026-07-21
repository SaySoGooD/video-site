import uuid
from datetime import UTC, datetime

from auth_test.application.auth.interfaces.i_refresh_token_usecase import (
    IRefreshTokenUseCase,
)
from auth_test.application.common.dto import AuthTokenDTO
from auth_test.application.common.errors import AuthenticationError
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.application.common.interfaces.security.i_token_service import (
    ITokenService,
)
from auth_test.entities.session.models import AuthSession
from auth_test.entities.session.value_objects import SessionId


class RefreshTokenUseCase(IRefreshTokenUseCase):
    """Exchange a valid refresh token for a fresh access + refresh pair.

    Refresh-token **rotation**: the presented session is revoked and a new one
    (new ``jti``) is issued, all in one transaction. So each refresh token is
    single-use — if a stolen one is replayed after the legitimate client has
    already refreshed, the session is already revoked and the replay fails
    (401), which surfaces the theft. Keeps access tokens short-lived without
    forcing the user to re-enter their password.
    """

    def __init__(self, uow: IUnitOfWork, token_service: ITokenService) -> None:
        self._uow = uow
        self._token_service = token_service

    async def __call__(self, refresh_token: str) -> AuthTokenDTO:
        payload = self._token_service.decode(refresh_token)

        if payload.token_type != "refresh":
            raise AuthenticationError("A refresh token is required")

        async with self._uow as uow:
            session = await uow.sessions.get_by_jti(payload.jti)
            if session is None or not session.is_valid():
                raise AuthenticationError("Refresh session is no longer valid")

            user = await uow.users.get_by_id(payload.user_id)
            if user is None or not user.is_active:
                raise AuthenticationError("User is inactive or missing")

            await uow.sessions.revoke(payload.jti)

            new_jti = uuid.uuid4().hex
            access = self._token_service.issue_access(user.id, new_jti)
            refresh = self._token_service.issue_refresh(user.id, new_jti)
            await uow.sessions.add(
                AuthSession(
                    id=SessionId(0),
                    user_id=user.id,
                    jti=new_jti,
                    created_at=datetime.now(UTC),
                    expires_at=refresh.expires_at,
                    revoked=False,
                )
            )
            await uow.commit()

        return AuthTokenDTO(
            access_token=access.token,
            refresh_token=refresh.token,
            token_type="bearer",
            access_expires_at=access.expires_at,
            refresh_expires_at=refresh.expires_at,
        )
