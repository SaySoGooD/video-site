from types import TracebackType

from auth_test.adapter.memory.repositories.permission_repository import (
    InMemoryPermissionRepository,
)
from auth_test.adapter.memory.repositories.role_repository import (
    InMemoryRoleRepository,
)
from auth_test.adapter.memory.repositories.session_repository import (
    InMemorySessionRepository,
)
from auth_test.adapter.memory.repositories.user_repository import (
    InMemoryUserRepository,
)
from auth_test.adapter.memory.storage import InMemoryStorage
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork


class InMemoryUnitOfWork(IUnitOfWork):
    """Mock unit of work backed by :class:`InMemoryStorage`.

    All repositories share the one storage singleton, so writes are visible
    across requests. Being a stub, it does not model transactions: mutations
    take effect immediately and ``commit``/``rollback`` are no-ops. The use
    cases validate before they mutate, so this is sufficient for a demo run
    without a database server.
    """

    def __init__(self, storage: InMemoryStorage) -> None:
        self._storage = storage

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        self.users = InMemoryUserRepository(self._storage)
        self.roles = InMemoryRoleRepository(self._storage)
        self.permissions = InMemoryPermissionRepository(self._storage)
        self.sessions = InMemorySessionRepository(self._storage)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None
