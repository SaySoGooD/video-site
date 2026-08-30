from abc import ABC, abstractmethod
from types import TracebackType

from users_service.application.common.interfaces.repositories.i_audit_log_repository import (  # noqa: E501
    IAuditLogRepository,
)
from users_service.application.common.interfaces.repositories.i_permission_repository import (  # noqa: E501
    IPermissionRepository,
)
from users_service.application.common.interfaces.repositories.i_role_repository import (
    IRoleRepository,
)
from users_service.application.common.interfaces.repositories.i_security_token_repository import (  # noqa: E501
    ISecurityTokenRepository,
)
from users_service.application.common.interfaces.repositories.i_session_repository import (  # noqa: E501
    ISessionRepository,
)
from users_service.application.common.interfaces.repositories.i_user_repository import (
    IUserRepository,
)


class IUnitOfWork(ABC):
    """Transactional boundary bundling every repository.

    A single use case runs inside one ``async with uow:`` block so that all of
    its writes commit or roll back together (atomicity + consistency). The
    repositories exposed here all share the same underlying transaction, and
    the context manager rolls back automatically if it exits with an error.
    """

    users: IUserRepository
    roles: IRoleRepository
    permissions: IPermissionRepository
    sessions: ISessionRepository
    security_tokens: ISecurityTokenRepository
    audit_log: IAuditLogRepository

    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork":
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Flush and commit the current transaction."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Discard all changes made in the current transaction."""
        ...
