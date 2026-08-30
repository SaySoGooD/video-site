from users_service.application.auth.interfaces.i_logout_usecase import ILogoutUseCase
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_token_service import (
    ITokenService,
)


class LogoutUseCase(ILogoutUseCase):
    """Revoke the session behind an access token.

    Logout is server-side: flipping the session's ``revoked`` flag makes the
    still-unexpired JWT unusable on the next request. An already-invalid token
    simply has nothing to revoke, so logout is idempotent and never errors.
    """

    def __init__(self, uow: IUnitOfWork, token_service: ITokenService) -> None:
        self._uow = uow
        self._token_service = token_service

    async def __call__(self, token: str) -> None:
        try:
            payload = self._token_service.decode(token)
        except Exception:
            return

        async with self._uow as uow:
            await uow.sessions.revoke(payload.jti)
            await uow.commit()
