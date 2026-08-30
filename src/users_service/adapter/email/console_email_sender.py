import logging

from users_service.application.common.dto import EmailMessageDTO
from users_service.application.common.interfaces.i_email_sender import IEmailSender

logger = logging.getLogger(__name__)


class ConsoleEmailSender(IEmailSender):
    """Writes the email to the log instead of sending it.

    The development default: it makes verification and reset links visible
    without an SMTP server. It is also why ``EMAIL_BACKEND`` must be set to
    ``smtp`` in production — otherwise every reset link ends up in the
    application log.
    """

    async def send(self, message: EmailMessageDTO) -> None:
        logger.info(
            "email (not sent) to=%s subject=%s\n%s",
            message.to,
            message.subject,
            message.body,
        )
