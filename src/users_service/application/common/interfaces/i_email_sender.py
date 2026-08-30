from abc import ABC, abstractmethod

from users_service.application.common.dto import EmailMessageDTO


class IEmailSender(ABC):
    """Port for delivering a transactional email.

    Implementations must not raise on delivery failure: a bounced
    verification mail is not a reason to fail a registration that already
    committed. They log instead, and the user asks for a new link.
    """

    @abstractmethod
    async def send(self, message: EmailMessageDTO) -> None:
        ...
