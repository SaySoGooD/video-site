from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from users_service.adapter.database.mappers.session_mapper import session_to_entity
from users_service.adapter.database.orm_models.session_orm import SessionORM
from users_service.application.common.interfaces.repositories.i_session_repository import (  # noqa: E501
    ISessionRepository,
)
from users_service.entities.session.models import AuthSession
from users_service.entities.session.value_objects import SessionId
from users_service.entities.user.value_objects import UserId


class SqlAlchemySessionRepository(ISessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, auth_session: AuthSession) -> AuthSession:
        row = SessionORM(
            user_id=int(auth_session.user_id),
            jti=auth_session.jti,
            created_at=auth_session.created_at,
            expires_at=auth_session.expires_at,
            revoked_at=auth_session.revoked_at,
            visitor_id=auth_session.visitor_id,
            user_agent=auth_session.user_agent,
            ip_address=auth_session.ip_address,
            device=auth_session.device,
            last_seen_at=auth_session.last_seen_at,
        )
        self._session.add(row)
        await self._session.flush()
        return session_to_entity(row)

    async def get_by_id(self, session_id: SessionId) -> AuthSession | None:
        row = await self._session.get(SessionORM, int(session_id))
        return session_to_entity(row) if row is not None else None

    async def get_by_jti(self, jti: str) -> AuthSession | None:
        result = await self._session.execute(
            select(SessionORM).where(SessionORM.jti == jti)
        )
        row = result.scalar_one_or_none()
        return session_to_entity(row) if row is not None else None

    async def list_active_for_user(self, user_id: UserId) -> list[AuthSession]:
        # Expiry is filtered in Python via the entity rather than in SQL:
        # backends differ in whether they hand back aware datetimes, and the
        # entity already owns that rule.
        result = await self._session.execute(
            select(SessionORM)
            .where(
                SessionORM.user_id == int(user_id),
                SessionORM.revoked_at.is_(None),
            )
            .order_by(SessionORM.id.desc())
        )
        sessions = [session_to_entity(row) for row in result.scalars().all()]
        return [s for s in sessions if s.is_valid()]

    async def revoke(self, jti: str, moment: datetime) -> None:
        await self._session.execute(
            update(SessionORM)
            .where(SessionORM.jti == jti, SessionORM.revoked_at.is_(None))
            .values(revoked_at=moment)
        )
        await self._session.flush()

    async def revoke_all_for_user(
        self,
        user_id: UserId,
        moment: datetime,
        except_jti: str | None = None,
    ) -> int:
        statement = (
            update(SessionORM)
            .where(
                SessionORM.user_id == int(user_id),
                SessionORM.revoked_at.is_(None),
            )
            .values(revoked_at=moment)
        )
        if except_jti is not None:
            statement = statement.where(SessionORM.jti != except_jti)

        result = await self._session.execute(statement)
        await self._session.flush()
        return int(result.rowcount or 0)
