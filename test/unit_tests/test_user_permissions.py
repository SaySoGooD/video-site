from users_service.entities.permission.models import Permission
from users_service.entities.permission.value_objects import PermissionId
from users_service.entities.role.models import Role
from users_service.entities.role.value_objects import RoleId
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import Email, UserId, Username


def _user(is_superuser: bool = False, roles: list[Role] | None = None) -> User:
    return User(
        id=UserId(1),
        email=Email("u@example.com"),
        username=Username("u"),
        password_hash="x",
        is_superuser=is_superuser,
        roles=roles or [],
    )


class TestUserHasPermission:
    def test_superuser_bypasses_role_check(self) -> None:
        assert _user(is_superuser=True).has_permission("anything", "at-all")

    def test_role_permission_grants_access(self) -> None:
        role = Role(
            id=RoleId(1),
            name="reader",
            permissions=[Permission(PermissionId(1), "account", "read")],
        )
        user = _user(roles=[role])
        assert user.has_permission("account", "read")
        assert not user.has_permission("account", "moderate")

    def test_no_roles_means_no_permissions(self) -> None:
        assert not _user().has_permission("account", "read")
