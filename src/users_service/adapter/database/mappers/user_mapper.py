from users_service.adapter.database.mappers.role_mapper import role_to_entity
from users_service.adapter.database.orm_models.user_orm import UserORM
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import (
    Email,
    UserId,
    Username,
    VisitorId,
)


def user_to_entity(row: UserORM) -> User:
    return User(
        id=UserId(row.id),
        email=Email(row.email),
        username=Username(row.username),
        password_hash=row.password_hash,
        display_name=row.display_name,
        is_active=row.is_active,
        is_superuser=row.is_superuser,
        visitor_id=(
            VisitorId(row.visitor_id) if row.visitor_id is not None else None
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
        roles=[role_to_entity(r) for r in row.roles],
    )
