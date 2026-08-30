import uuid
from datetime import UTC, datetime

from users_service.application.auth.interfaces.i_refresh_token_usecase import (
    IRefreshTokenUseCase,
)
from users_service.application.common.dto import (
    AuthResultDTO,
    AuthTokenDTO,
    DeviceInfoDTO,
)
from users_service.application.common.errors import AuthenticationError
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_token_service import (
    ITokenService,
)
from users_service.entities.session.models import AuthSession
from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.value_objects import VisitorId


class RefreshTokenUseCase(IRefreshTokenUseCase):
    """Exchange a valid refresh token for a fresh access + refresh pair.

    Refresh-token **rotation**: the presented session is revoked and a new one
    (new ``jti``) is issued, all in one transaction. So each refresh token is
    single-use — if a stolen one is replayed after the legitimate client has
    already refreshed, the session is already revoked and the replay fails
    (401), which surfaces the theft. Keeps access tokens short-lived without
    forcing the user to re-enter their password.

    The rotated session inherits the device details of the one it replaces, so
    a refresh does not look like a new login in ``GET /users/me/sessions``;
    only the fields the current request actually knows are refreshed.
    """

    def __init__(self, uow: IUnitOfWork, token_service: ITokenService) -> None:
        self._uow = uow
        self._token_service = token_service

    async def __call__(
        self, refresh_token: str, device: DeviceInfoDTO | None = None
    ) -> AuthResultDTO:
        device = device or DeviceInfoDTO()
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

            visitor_id = device.visitor_id or session.visitor_id
            await uow.sessions.add(
                AuthSession(
                    id=SessionId(0),
                    user_id=user.id,
                    jti=new_jti,
                    created_at=session.created_at,
                    expires_at=refresh.expires_at,
                    revoked=False,
                    visitor_id=(
                        VisitorId(visitor_id) if visitor_id is not None else None
                    ),
                    user_agent=device.user_agent or session.user_agent,
                    ip_address=device.ip_address or session.ip_address,
                    last_used_at=datetime.now(UTC),
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
