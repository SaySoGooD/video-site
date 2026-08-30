from datetime import UTC, datetime

from users_service.application.auth.interfaces.i_verify_email_usecase import (
    IVerifyEmailUseCase,
)
from users_service.application.common import audit, user_cache_codec
from users_service.application.common.dto import DeviceInfoDTO
from users_service.application.common.errors import InvalidTokenError
from users_service.application.common.interfaces.i_cache import ICache
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_one_time_token_service import (  # noqa: E501
    IOneTimeTokenService,
)
from users_service.entities.audit.value_objects import AuditAction
from users_service.entities.security_token.value_objects import TokenPurpose
from users_service.entities.user.models import User


class VerifyEmailUseCase(IVerifyEmailUseCase):
    """Spend a mailed verification token and stamp ``email_verified_at``.

    The presented secret is hashed and looked up by hash, so the stored row
    never contains anything that could be mailed. Unknown, spent and expired
    tokens all raise the same error — distinguishing them would confirm which
    links exist.

    Verifying twice is not an error the second time only in the sense that the
    *link* is spent: an already-verified account simply keeps its original
    timestamp.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        one_time_tokens: IOneTimeTokenService,
        cache: ICache,
    ) -> None:
        self._uow = uow
        self._one_time_tokens = one_time_tokens
        self._cache = cache

    async def __call__(
        self, token: str, device: DeviceInfoDTO | None = None
    ) -> User:
        token_hash = self._one_time_tokens.hash(token)

        async with self._uow as uow:
            stored = await uow.security_tokens.get_by_hash(
                token_hash, TokenPurpose.EMAIL_VERIFICATION
            )
            if stored is None or not stored.is_usable():
                raise InvalidTokenError()

            user = await uow.users.get_by_id(stored.user_id)
            if user is None or not user.is_active:
                raise InvalidTokenError()

            await uow.security_tokens.mark_used(stored)

            if not user.is_email_verified:
                user.email_verified_at = datetime.now(UTC)
                user = await uow.users.update(user)

            await audit.record(
                uow,
                AuditAction.EMAIL_VERIFIED,
                user_id=user.id,
                device=device,
                email=str(user.email),
            )
            await uow.commit()

        await self._cache.delete(user_cache_codec.user_cache_key(user.id))
        return user
