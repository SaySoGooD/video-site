from datetime import UTC, datetime

from users_service.application.auth.interfaces.i_reset_password_usecase import (
    IResetPasswordUseCase,
)
from users_service.application.common import audit, user_cache_codec
from users_service.application.common.dto import DeviceInfoDTO, ResetPasswordDTO
from users_service.application.common.errors import (
    InvalidTokenError,
    PasswordMismatchError,
    RateLimitedError,
)
from users_service.application.common.interfaces.i_cache import ICache
from users_service.application.common.interfaces.i_rate_limiter import IRateLimiter
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_one_time_token_service import (  # noqa: E501
    IOneTimeTokenService,
)
from users_service.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)
from users_service.application.common.rate_limit_policy import RateLimitPolicy
from users_service.entities.audit.value_objects import AuditAction
from users_service.entities.security_token.value_objects import TokenPurpose


class ResetPasswordUseCase(IResetPasswordUseCase):
    """Set a new password from a mailed token and sign every device out.

    Revoking all sessions is the point of the flow, not a nicety: a password
    is usually reset because someone else may have had it, and leaving their
    already-issued refresh token alive would make the reset cosmetic. The
    password change, the token being spent, the session revocations and the
    audit row all commit together.

    Any other outstanding reset link is spent as well, so a second email
    sitting in the same inbox cannot be used to take the account back.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        one_time_tokens: IOneTimeTokenService,
        cache: ICache,
        limiter: IRateLimiter,
        ip_policy: RateLimitPolicy,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._one_time_tokens = one_time_tokens
        self._cache = cache
        self._limiter = limiter
        self._ip_policy = ip_policy

    async def __call__(
        self, data: ResetPasswordDTO, device: DeviceInfoDTO | None = None
    ) -> None:
        device = device or DeviceInfoDTO()
        await self._check_rate_limit(device)

        if data.password != data.password_repeat:
            raise PasswordMismatchError()

        token_hash = self._one_time_tokens.hash(data.token)

        async with self._uow as uow:
            stored = await uow.security_tokens.get_by_hash(
                token_hash, TokenPurpose.PASSWORD_RESET
            )
            if stored is None or not stored.is_usable():
                raise InvalidTokenError()

            user = await uow.users.get_by_id(stored.user_id)
            if user is None or not user.is_active:
                raise InvalidTokenError()

            now = datetime.now(UTC)
            user.password_hash = self._hasher.hash(data.password)
            await uow.users.update_password(user)

            await uow.security_tokens.mark_used(stored)
            await uow.security_tokens.invalidate_for_user(
                user.id, TokenPurpose.PASSWORD_RESET
            )
            revoked = await uow.sessions.revoke_all_for_user(user.id, now)

            await audit.record(
                uow,
                AuditAction.PASSWORD_RESET,
                user_id=user.id,
                device=device,
                sessions_revoked=revoked,
            )
            await uow.commit()

        await self._cache.delete(user_cache_codec.user_cache_key(user.id))

    async def _check_rate_limit(self, device: DeviceInfoDTO) -> None:
        """Cap reset attempts per IP so tokens cannot be guessed in bulk."""
        if not self._ip_policy.is_enforced or device.ip_address is None:
            return

        decision = await self._limiter.hit(
            f"reset-password:ip:{device.ip_address}",
            self._ip_policy.limit,
            self._ip_policy.window_seconds,
        )
        if not decision.allowed:
            raise RateLimitedError(decision.retry_after_seconds)
