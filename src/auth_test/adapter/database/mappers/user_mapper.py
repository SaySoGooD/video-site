from auth_test.adapter.database.mappers.role_mapper import role_to_entity
from auth_test.adapter.database.orm_models.user_orm import UserORM
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import Email, UserId


def user_to_entity(row: UserORM) -> User:
    return User(
        id=UserId(row.id),
        email=Email(row.email),
        password_hash=row.password_hash,
        first_name=row.first_name,
        last_name=row.last_name,
        middle_name=row.middle_name,
        is_active=row.is_active,
        is_superuser=row.is_superuser,
        created_at=row.created_at,
        updated_at=row.updated_at,
        roles=[role_to_entity(r) for r in row.roles],
    )
