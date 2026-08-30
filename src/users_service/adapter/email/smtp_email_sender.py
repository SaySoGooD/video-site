import asyncio
import logging
import smtplib
from email.message import EmailMessage

from users_service.application.common.dto import EmailMessageDTO
from users_service.application.common.interfaces.i_email_sender import IEmailSender

logger = logging.getLogger(__name__)


class SmtpEmailSender(IEmailSender):
    """Sends mail over SMTP, off the event loop.

    ``smtplib`` is blocking, so the send runs in a worker thread — otherwise a
    slow mail server would stall every other request in the process.

    Delivery failures are logged, never raised: the account was already
    created or the reset token already stored, and unwinding that because a
    mail server was briefly unavailable would be worse than a missing email
    the user can simply request again.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        sender: str,
        use_tls: bool,
        timeout_seconds: int = 10,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._use_tls = use_tls
        self._timeout_seconds = timeout_seconds

    async def send(self, message: EmailMessageDTO) -> None:
        try:
            await asyncio.to_thread(self._send_blocking, message)
        except Exception:
            logger.exception("failed to send email to %s", message.to)

    def _send_blocking(self, message: EmailMessageDTO) -> None:
        mail = EmailMessage()
        mail["From"] = self._sender
        mail["To"] = message.to
        mail["Subject"] = message.subject
        mail.set_content(message.body)

        with smtplib.SMTP(
            self._host, self._port, timeout=self._timeout_seconds
        ) as client:
            if self._use_tls:
                client.starttls()
            if self._username and self._password:
                client.login(self._username, self._password)
            client.send_message(mail)
