from datetime import UTC, datetime, timedelta

from users_service.application.auth.interfaces.i_forgot_password_usecase import (
    IForgotPasswordUseCase,
)
from users_service.application.common.dto import DeviceInfoDTO, EmailMessageDTO
from users_service.application.common.errors import RateLimitedError
from users_service.application.common.interfaces.i_email_sender import IEmailSender
from users_service.application.common.interfaces.i_rate_limiter import IRateLimiter
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_one_time_token_service import (  # noqa: E501
    IOneTimeTokenService,
)
from users_service.application.common.rate_limit_policy import RateLimitPolicy
from users_service.entities.security_token.models import SecurityToken
from users_service.entities.security_token.value_objects import (
    SecurityTokenId,
    TokenPurpose,
)


class ForgotPasswordUseCase(IForgotPasswordUseCase):
    """Mail a password reset link, if the address belongs to an account.

    The caller is told nothing either way: the endpoint answers identically
    for a known and an unknown address, or this becomes a way to enumerate
    which emails have accounts here — which, for a site like this one, is a
    privacy problem well beyond the usual.

    Requesting a new link invalidates any earlier one, so a forwarded or
    leaked older email stops working.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        one_time_tokens: IOneTimeTokenService,
        email_sender: IEmailSender,
        limiter: IRateLimiter,
        email_policy: RateLimitPolicy,
        ip_policy: RateLimitPolicy,
        reset_url_template: str,
        reset_ttl_minutes: int,
    ) -> None:
        self._uow = uow
        self._one_time_tokens = one_time_tokens
        self._email_sender = email_sender
        self._limiter = limiter
        self._email_policy = email_policy
        self._ip_policy = ip_policy
        self._reset_url_template = reset_url_template
        self._reset_ttl_minutes = reset_ttl_minutes

    async def __call__(
        self, email: str, device: DeviceInfoDTO | None = None
    ) -> None:
        device = device or DeviceInfoDTO()
        address = email.strip().lower()
        await self._check_rate_limits(address, device)

        async with self._uow as uow:
            user = await uow.users.get_by_email(address)
            if user is None or not user.is_active:
                return  # Same visible outcome as success.

            await uow.security_tokens.invalidate_for_user(
                user.id, TokenPurpose.PASSWORD_RESET
            )

            secret = self._one_time_tokens.generate()
            now = datetime.now(UTC)
            await uow.security_tokens.add(
                SecurityToken(
                    id=SecurityTokenId(0),
                    user_id=user.id,
                    purpose=TokenPurpose.PASSWORD_RESET,
                    token_hash=secret.hashed,
                    created_at=now,
                    expires_at=now + timedelta(minutes=self._reset_ttl_minutes),
                )
            )
            await uow.commit()

        await self._email_sender.send(
            EmailMessageDTO(
                to=address,
                subject="Reset your password",
                body=(
                    "Someone asked to reset the password for this account.\n\n"
                    f"{self._reset_url_template.format(token=secret.plain)}\n\n"
                    f"The link expires in {self._reset_ttl_minutes} minutes. "
                    "If this was not you, you can ignore this email — nothing "
                    "has changed."
                ),
            )
        )

    async def _check_rate_limits(self, address: str, device: DeviceInfoDTO) -> None:
        """Cap requests per address and per IP.

        Without the per-address cap this endpoint is a free mail cannon aimed
        at whichever inbox an attacker picks.
        """
        if self._email_policy.is_enforced:
            decision = await self._limiter.hit(
                f"forgot-password:{address}",
                self._email_policy.limit,
                self._email_policy.window_seconds,
            )
            if not decision.allowed:
                raise RateLimitedError(decision.retry_after_seconds)

        if self._ip_policy.is_enforced and device.ip_address is not None:
            decision = await self._limiter.hit(
                f"forgot-password:ip:{device.ip_address}",
                self._ip_policy.limit,
                self._ip_policy.window_seconds,
            )
            if not decision.allowed:
                raise RateLimitedError(decision.retry_after_seconds)
