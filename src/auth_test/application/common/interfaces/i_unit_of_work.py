from abc import ABC, abstractmethod
from types import TracebackType

from auth_test.application.common.interfaces.repositories.i_permission_repository import (
    IPermissionRepository,
)
from auth_test.application.common.interfaces.repositories.i_role_repository import (
    IRoleRepository,
)
from auth_test.application.common.interfaces.repositories.i_session_repository import (
    ISessionRepository,
)
from auth_test.application.common.interfaces.repositories.i_user_repository import (
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
