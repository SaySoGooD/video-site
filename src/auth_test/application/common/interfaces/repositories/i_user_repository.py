from abc import ABC, abstractmethod

from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import UserId


class IUserRepository(ABC):
    """Persistence port for users and their role assignments."""

    @abstractmethod
    async def add(self, user: User) -> User:
        """Insert a new user and return it with its generated id."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        """Return the user (with roles and permissions) or ``None``."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Return the user (with roles and permissions) or ``None``."""
        ...

    @abstractmethod
    async def list_all(self) -> list[User]:
        """Return every user, active or not."""
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        """Persist mutable fields of an existing user."""
        ...

    @abstractmethod
    async def assign_role(self, user_id: UserId, role_id: RoleId) -> None:
        """Grant a role to a user (idempotent)."""
        ...

    @abstractmethod
    async def revoke_role(self, user_id: UserId, role_id: RoleId) -> None:
        """Remove a role from a user (idempotent)."""
        ...
