"""Issuing and mailing an email-verification link.

Two flows need it — signing up and changing an address — and both must invalidate
whatever link was outstanding before. Keeping that in one place means the two
cannot drift apart, and neither use case has to know how a token is minted.
"""

from datetime import UTC, datetime, timedelta

from users_service.application.common.dto import EmailMessageDTO
from users_service.application.common.interfaces.i_email_sender import IEmailSender
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_one_time_token_service import (  # noqa: E501
    IOneTimeTokenService,
)
from users_service.entities.security_token.models import SecurityToken
from users_service.entities.security_token.value_objects import (
    SecurityTokenId,
    TokenPurpose,
)
from users_service.entities.user.value_objects import UserId


class EmailVerificationIssuer:
    def __init__(
        self,
        one_time_tokens: IOneTimeTokenService,
        email_sender: IEmailSender,
        url_template: str,
        ttl_hours: int,
    ) -> None:
        self._one_time_tokens = one_time_tokens
        self._email_sender = email_sender
        self._url_template = url_template
        self._ttl_hours = ttl_hours

    async def issue(self, uow: IUnitOfWork, user_id: UserId) -> str:
        """Store a fresh token inside the caller's transaction; return the secret.

        Any earlier verification link for the user is spent first, so only the
        newest email works.
        """
        await uow.security_tokens.invalidate_for_user(
            user_id, TokenPurpose.EMAIL_VERIFICATION
        )

        secret = self._one_time_tokens.generate()
        now = datetime.now(UTC)
        await uow.security_tokens.add(
            SecurityToken(
                id=SecurityTokenId(0),
                user_id=user_id,
                purpose=TokenPurpose.EMAIL_VERIFICATION,
                token_hash=secret.hashed,
                created_at=now,
                expires_at=now + timedelta(hours=self._ttl_hours),
            )
        )
        return secret.plain

    async def send(self, email: str, secret: str) -> None:
        """Mail the link. Call this *after* the transaction has committed."""
        await self._email_sender.send(
            EmailMessageDTO(
                to=email,
                subject="Confirm your email address",
                body=(
                    "Confirm your email address to finish setting up your "
                    "account:\n\n"
                    f"{self._url_template.format(token=secret)}\n\n"
                    f"The link expires in {self._ttl_hours} hours."
                ),
            )
        )
