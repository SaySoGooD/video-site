import uuid
from datetime import UTC, datetime

from users_service.application.auth.interfaces.i_login_usecase import ILoginUseCase
from users_service.application.common.dto import (
    AuthResultDTO,
    AuthTokenDTO,
    DeviceInfoDTO,
    LoginDTO,
)
from users_service.application.common.errors import InvalidCredentialsError
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)
from users_service.application.common.interfaces.security.i_token_service import (
    ITokenService,
)
from users_service.entities.session.models import AuthSession
from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.value_objects import VisitorId


class LoginUseCase(ILoginUseCase):
    """Verify credentials and issue an access + refresh token pair.

    A wrong password and an unknown/inactive account produce the *same* error
    so the endpoint cannot be used to probe which emails exist. On success one
    session row is written; its ``jti`` is embedded in both tokens, giving the
    server a handle to revoke them later (logout / soft-delete / refresh
    rotation). The session lives as long as the refresh token, and records the
    device it was created from so the user can review it later.
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

    async def __call__(
        self, data: LoginDTO, device: DeviceInfoDTO | None = None
    ) -> AuthResultDTO:
        device = device or DeviceInfoDTO()

        async with self._uow as uow:
            user = await uow.users.get_by_email(data.email.strip().lower())

            if user is None or not user.is_active:
                raise InvalidCredentialsError()

            if not self._hasher.verify(data.password, user.password_hash):
                raise InvalidCredentialsError()

            jti = uuid.uuid4().hex
            access = self._token_service.issue_access(user.id, jti)
            refresh = self._token_service.issue_refresh(user.id, jti)

            now = datetime.now(UTC)
            await uow.sessions.add(
                AuthSession(
                    id=SessionId(0),
                    user_id=user.id,
                    jti=jti,
                    created_at=now,
                    expires_at=refresh.expires_at,
                    revoked=False,
                    visitor_id=(
                        VisitorId(device.visitor_id)
                        if device.visitor_id is not None
                        else None
                    ),
                    user_agent=device.user_agent,
                    ip_address=device.ip_address,
                    last_used_at=now,
                )
            )
            await uow.commit()

        return AuthResultDTO(
            tokens=AuthTokenDTO(
                access_token=access.token,
                refresh_token=refresh.token,
                token_type="bearer",
                access_expires_at=access.expires_at,
                refresh_expires_at=refresh.expires_at,
            ),
            user=user,
        )
