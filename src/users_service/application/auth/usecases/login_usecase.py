import uuid
from datetime import UTC, datetime

from users_service.application.auth.interfaces.i_login_usecase import ILoginUseCase
from users_service.application.common import audit
from users_service.application.common.dto import (
    AuthResultDTO,
    AuthTokenDTO,
    DeviceInfoDTO,
    LoginDTO,
)
from users_service.application.common.errors import (
    AccountLockedError,
    InvalidCredentialsError,
    RateLimitedError,
)
from users_service.application.common.interfaces.i_rate_limiter import IRateLimiter
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)
from users_service.application.common.interfaces.security.i_token_service import (
    ITokenService,
)
from users_service.application.common.rate_limit_policy import RateLimitPolicy
from users_service.entities.audit.value_objects import AuditAction
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

    Brute force is capped from **two** directions, because either alone is
    porous: a per-IP counter stops one host hammering many accounts, and a
    per-account counter stops a botnet spread over thousands of IPs hammering
    one account. Exceeding the per-account limit locks that account for the
    rest of the window; a successful login clears its counter.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        token_service: ITokenService,
        limiter: IRateLimiter,
        ip_policy: RateLimitPolicy,
        account_policy: RateLimitPolicy,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._token_service = token_service
        self._limiter = limiter
        self._ip_policy = ip_policy
        self._account_policy = account_policy

    async def __call__(
        self, data: LoginDTO, device: DeviceInfoDTO | None = None
    ) -> AuthResultDTO:
        device = device or DeviceInfoDTO()
        email = data.email.strip().lower()

        await self._guard_ip(device)
        await self._guard_account(email)

        async with self._uow as uow:
            user = await uow.users.get_by_email(email)
            valid = user is not None and user.is_active and self._hasher.verify(
                data.password, user.password_hash
            )

            if not valid:
                await self._count_failure(email, device)
                await audit.record(
                    uow,
                    AuditAction.LOGIN_FAILED,
                    user_id=user.id if user is not None else None,
                    device=device,
                    email=email,
                    reason=(
                        "unknown_account"
                        if user is None
                        else "inactive"
                        if not user.is_active
                        else "bad_password"
                    ),
                )
                await uow.commit()
                raise InvalidCredentialsError()

            assert user is not None
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
                    visitor_id=(
                        VisitorId(device.visitor_id)
                        if device.visitor_id is not None
                        else None
                    ),
                    user_agent=device.user_agent,
                    ip_address=device.ip_address,
                    device=device.device,
                    last_seen_at=now,
                )
            )
            await audit.record(
                uow,
                AuditAction.LOGIN,
                user_id=user.id,
                device=device,
                visitor_id=device.visitor_id,
            )
            await uow.commit()

        await self._limiter.reset(self._account_key(email))

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

    async def _guard_ip(self, device: DeviceInfoDTO) -> None:
        if not self._ip_policy.is_enforced or device.ip_address is None:
            return

        decision = await self._limiter.peek(
            f"login:ip:{device.ip_address}", self._ip_policy.limit
        )
        if not decision.allowed:
            raise RateLimitedError(
                decision.retry_after_seconds,
                "Too many login attempts from this address",
            )

    async def _guard_account(self, email: str) -> None:
        if not self._account_policy.is_enforced:
            return

        decision = await self._limiter.peek(
            self._account_key(email), self._account_policy.limit
        )
        if not decision.allowed:
            raise AccountLockedError(decision.retry_after_seconds)

    async def _count_failure(self, email: str, device: DeviceInfoDTO) -> None:
        """Charge a failed attempt to both counters.

        Only failures count: a user with many devices logging in legitimately
        should never approach the limit.
        """
        if self._ip_policy.is_enforced and device.ip_address is not None:
            await self._limiter.hit(
                f"login:ip:{device.ip_address}",
                self._ip_policy.limit,
                self._ip_policy.window_seconds,
            )

        if self._account_policy.is_enforced:
            await self._limiter.hit(
                self._account_key(email),
                self._account_policy.limit,
                self._account_policy.window_seconds,
            )

    @staticmethod
    def _account_key(email: str) -> str:
        return f"login:user:{email}"
