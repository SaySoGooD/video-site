from auth_test.adapter.database.mappers.permission_mapper import (
    permission_to_entity,
)
from auth_test.adapter.database.orm_models.role_orm import RoleORM
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId


def role_to_entity(row: RoleORM) -> Role:
    return Role(
        id=RoleId(row.id),
        name=row.name,
        description=row.description,
        permissions=[permission_to_entity(p) for p in row.permissions],
    )
