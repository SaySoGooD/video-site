import uuid
from datetime import UTC, datetime

from auth_test.application.auth.interfaces.i_login_usecase import ILoginUseCase
from auth_test.application.common.dto import AuthTokenDTO, LoginDTO
from auth_test.application.common.errors import InvalidCredentialsError
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)
from auth_test.application.common.interfaces.security.i_token_service import (
    ITokenService,
)
from auth_test.entities.session.models import AuthSession
from auth_test.entities.session.value_objects import SessionId


class LoginUseCase(ILoginUseCase):
    """Verify credentials and issue an access + refresh token pair.

    A wrong password and an unknown/inactive account produce the *same* error
    so the endpoint cannot be used to probe which emails exist. On success one
    session row is written; its ``jti`` is embedded in both tokens, giving the
    server a handle to revoke them later (logout / soft-delete / refresh
    rotation). The session lives as long as the refresh token.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        token_service: ITokenService,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._token_service = token_service

    async def __call__(self, data: LoginDTO) -> AuthTokenDTO:
        async with self._uow as uow:
            user = await uow.users.get_by_email(data.email)

            if user is None or not user.is_active:
                raise InvalidCredentialsError()

            if not self._hasher.verify(data.password, user.password_hash):
                raise InvalidCredentialsError()

            jti = uuid.uuid4().hex
            access = self._token_service.issue_access(user.id, jti)
            refresh = self._token_service.issue_refresh(user.id, jti)

            await uow.sessions.add(
                AuthSession(
                    id=SessionId(0),
                    user_id=user.id,
                    jti=jti,
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
