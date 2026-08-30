from users_service.application.auth.interfaces.i_register_user_usecase import (
    IRegisterUserUseCase,
)
from users_service.application.auth.services.email_verification_issuer import (
    EmailVerificationIssuer,
)
from users_service.application.common import audit
from users_service.application.common.dto import DeviceInfoDTO, RegisterUserDTO
from users_service.application.common.errors import (
    EmailAlreadyExistsError,
    PasswordMismatchError,
    RateLimitedError,
    UsernameAlreadyExistsError,
)
from users_service.application.common.interfaces.i_rate_limiter import IRateLimiter
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)
from users_service.application.common.rate_limit_policy import RateLimitPolicy
from users_service.entities.audit.value_objects import AuditAction
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import (
    Email,
    UserId,
    Username,
    VisitorId,
)


class RegisterUserUseCase(IRegisterUserUseCase):
    """Create a new, unverified account with a hashed password.

    One transaction covers the uniqueness checks, the insert, the default-role
    grant, the verification token and the audit row: an account is never left
    without a role, and the audit log never claims a signup that rolled back.

    The verification email is sent *after* the commit — on purpose. Mail is the
    one step that talks to the outside world and may be slow or fail, and a
    signup that succeeded must not be undone because a mail server hiccuped.
    The user can always ask for a new link.

    The browser's ``visitor_id`` is stored on the account, which is the one
    place where "who is this user?" and "what did this visitor do?" are tied
    together — the analytics side reads that link, never the other way round.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        verification: EmailVerificationIssuer,
        limiter: IRateLimiter,
        ip_policy: RateLimitPolicy,
        default_role_name: str,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._verification = verification
        self._limiter = limiter
        self._ip_policy = ip_policy
        self._default_role_name = default_role_name

    async def __call__(
        self, data: RegisterUserDTO, device: DeviceInfoDTO | None = None
    ) -> User:
        device = device or DeviceInfoDTO()
        await self._check_rate_limit(device)

        if data.password != data.password_repeat:
            raise PasswordMismatchError()

        email = data.email.strip().lower()
        username = data.username.strip()

        async with self._uow as uow:
            if await uow.users.get_by_email(email) is not None:
                raise EmailAlreadyExistsError()
            if await uow.users.get_by_username(username) is not None:
                raise UsernameAlreadyExistsError()

            user = User(
                id=UserId(0),
                email=Email(email),
                username=Username(username),
                password_hash=self._hasher.hash(data.password),
                display_name=data.display_name,
                is_active=True,
                is_superuser=False,
                visitor_id=(
                    VisitorId(data.visitor_id)
                    if data.visitor_id is not None
                    else None
                ),
            )
            created = await uow.users.add(user)

            default_role = await uow.roles.get_by_name(self._default_role_name)
            if default_role is not None:
                await uow.users.assign_role(created.id, default_role.id)

            secret = await self._verification.issue(uow, created.id)

            await audit.record(
                uow,
                AuditAction.REGISTER,
                user_id=created.id,
                device=device,
                username=username,
                visitor_id=data.visitor_id,
            )
            await uow.commit()

            stored = await uow.users.get_by_id(created.id)

        await self._verification.send(email, secret)

        return stored if stored is not None else created

    async def _check_rate_limit(self, device: DeviceInfoDTO) -> None:
        """Cap signups per IP so the account table cannot be flooded."""
        if not self._ip_policy.is_enforced or device.ip_address is None:
            return

        decision = await self._limiter.hit(
            f"register:ip:{device.ip_address}",
            self._ip_policy.limit,
            self._ip_policy.window_seconds,
        )
        if not decision.allowed:
            raise RateLimitedError(
                decision.retry_after_seconds,
                "Too many accounts created from this address",
            )
