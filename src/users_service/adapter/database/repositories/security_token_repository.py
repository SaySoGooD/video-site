from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from users_service.adapter.database.mappers.security_token_mapper import (
    security_token_to_entity,
)
from users_service.adapter.database.orm_models.security_token_orm import (
    SecurityTokenORM,
)
from users_service.application.common.interfaces.repositories.i_security_token_repository import (  # noqa: E501
    ISecurityTokenRepository,
)
from users_service.entities.security_token.models import SecurityToken
from users_service.entities.security_token.value_objects import TokenPurpose
from users_service.entities.user.value_objects import UserId


class SqlAlchemySecurityTokenRepository(ISecurityTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: SecurityToken) -> SecurityToken:
        row = SecurityTokenORM(
            user_id=int(token.user_id),
            purpose=str(token.purpose),
            token_hash=token.token_hash,
            created_at=token.created_at,
            expires_at=token.expires_at,
            used_at=token.used_at,
        )
        self._session.add(row)
        await self._session.flush()
        return security_token_to_entity(row)

    async def get_by_hash(
        self, token_hash: str, purpose: TokenPurpose
    ) -> SecurityToken | None:
        result = await self._session.execute(
            select(SecurityTokenORM).where(
                SecurityTokenORM.token_hash == token_hash,
                SecurityTokenORM.purpose == str(purpose),
            )
        )
        row = result.scalar_one_or_none()
        return security_token_to_entity(row) if row is not None else None

    async def mark_used(self, token: SecurityToken) -> None:
        await self._session.execute(
            update(SecurityTokenORM)
            .where(
                SecurityTokenORM.id == int(token.id),
                SecurityTokenORM.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
        await self._session.flush()

    async def invalidate_for_user(
        self, user_id: UserId, purpose: TokenPurpose
    ) -> None:
        await self._session.execute(
            update(SecurityTokenORM)
            .where(
                SecurityTokenORM.user_id == int(user_id),
                SecurityTokenORM.purpose == str(purpose),
                SecurityTokenORM.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
        await self._session.flush()
