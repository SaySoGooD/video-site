from dataclasses import replace
from datetime import UTC, datetime

from auth_test.adapter.memory.storage import InMemoryStorage
from auth_test.application.common.interfaces.repositories.i_user_repository import (
    IUserRepository,
)
from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import UserId


class InMemoryUserRepository(IUserRepository):
    def __init__(self, storage: InMemoryStorage) -> None:
        self._storage = storage

    async def add(self, user: User) -> User:
        user_id = UserId(self._storage.next_id("user"))
        now = datetime.now(UTC)
        self._storage.users[user_id] = replace(
            user, id=user_id, created_at=now, updated_at=now, roles=[]
        )
        return self._storage.build_user(user_id)

    async def get_by_id(self, user_id: UserId) -> User | None:
        if user_id not in self._storage.users:
            return None
        return self._storage.build_user(user_id)

    async def get_by_email(self, email: str) -> User | None:
        for user_id, user in self._storage.users.items():
            if user.email == email:
                return self._storage.build_user(user_id)
        return None

    async def list_all(self) -> list[User]:
        return [self._storage.build_user(uid) for uid in sorted(self._storage.users)]

    async def update(self, user: User) -> User:
        existing = self._storage.users.get(user.id)
        if existing is None:
            raise ValueError(f"User {user.id} disappeared during update")
        self._storage.users[user.id] = replace(
            existing,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            middle_name=user.middle_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            updated_at=datetime.now(UTC),
        )
        return self._storage.build_user(user.id)

    async def assign_role(self, user_id: UserId, role_id: RoleId) -> None:
        self._storage.user_roles.add((int(user_id), int(role_id)))

    async def revoke_role(self, user_id: UserId, role_id: RoleId) -> None:
        self._storage.user_roles.discard((int(user_id), int(role_id)))
