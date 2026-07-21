from auth_test.adapter.database.orm_models.permission_orm import PermissionORM
from auth_test.entities.permission.models import Permission
from auth_test.entities.permission.value_objects import PermissionId


def permission_to_entity(row: PermissionORM) -> Permission:
    return Permission(
        id=PermissionId(row.id),
        resource=row.resource,
        action=row.action,
        description=row.description,
    )
