from auth_test.entities.permission.models import Permission
from auth_test.entities.permission.value_objects import PermissionId
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import Email, UserId


def _user(is_superuser: bool = False, roles: list[Role] | None = None) -> User:
    return User(
        id=UserId(1),
        email=Email("u@example.com"),
        password_hash="x",
        first_name="U",
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
            permissions=[Permission(PermissionId(1), "document", "read")],
        )
        user = _user(roles=[role])
        assert user.has_permission("document", "read")
        assert not user.has_permission("document", "delete")

    def test_no_roles_means_no_permissions(self) -> None:
        assert not _user().has_permission("document", "read")
