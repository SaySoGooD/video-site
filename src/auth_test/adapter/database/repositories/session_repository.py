from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth_test.adapter.database.mappers.session_mapper import session_to_entity
from auth_test.adapter.database.orm_models.session_orm import SessionORM
from auth_test.application.common.interfaces.repositories.i_session_repository import (
    ISessionRepository,
)
from auth_test.entities.session.models import AuthSession
from auth_test.entities.user.value_objects import UserId


class SqlAlchemySessionRepository(ISessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, auth_session: AuthSession) -> AuthSession:
        row = SessionORM(
            user_id=int(auth_session.user_id),
            jti=auth_session.jti,
            created_at=auth_session.created_at,
            expires_at=auth_session.expires_at,
            revoked=auth_session.revoked,
        )
        self._session.add(row)
        await self._session.flush()
        return session_to_entity(row)

    async def get_by_jti(self, jti: str) -> AuthSession | None:
        result = await self._session.execute(
            select(SessionORM).where(SessionORM.jti == jti)
        )
        row = result.scalar_one_or_none()
        return session_to_entity(row) if row is not None else None

    async def revoke(self, jti: str) -> None:
        await self._session.execute(
            update(SessionORM).where(SessionORM.jti == jti).values(revoked=True)
        )
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: UserId) -> None:
        await self._session.execute(
            update(SessionORM)
            .where(SessionORM.user_id == int(user_id))
            .values(revoked=True)
        )
        await self._session.flush()
