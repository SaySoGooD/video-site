from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_test.adapter.database.repositories.permission_repository import (
    SqlAlchemyPermissionRepository,
)
from auth_test.adapter.database.repositories.role_repository import (
    SqlAlchemyRoleRepository,
)
from auth_test.adapter.database.repositories.session_repository import (
    SqlAlchemySessionRepository,
)
from auth_test.adapter.database.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """One database transaction shared by all repositories.

    Constructed fresh per request (DI ``Factory``). Entering the context opens
    a session and binds the repositories to it; leaving it rolls back any
    uncommitted work and closes the session. Use cases call :meth:`commit`
    explicitly once their writes are consistent, giving ACID atomicity.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self._session)
        self.roles = SqlAlchemyRoleRepository(self._session)
        self.permissions = SqlAlchemyPermissionRepository(self._session)
        self.sessions = SqlAlchemySessionRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()
