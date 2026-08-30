from users_service.adapter.database.mappers.permission_mapper import (
    permission_to_entity,
)
from users_service.adapter.database.orm_models.role_orm import RoleORM
from users_service.entities.role.models import Role
from users_service.entities.role.value_objects import RoleId


def role_to_entity(row: RoleORM) -> Role:
    return Role(
        id=RoleId(row.id),
        name=row.name,
        description=row.description,
        permissions=[permission_to_entity(p) for p in row.permissions],
    )
