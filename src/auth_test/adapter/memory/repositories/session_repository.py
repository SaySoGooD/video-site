from dataclasses import replace

from auth_test.adapter.memory.storage import InMemoryStorage
from auth_test.application.common.interfaces.repositories.i_session_repository import (
    ISessionRepository,
)
from auth_test.entities.session.models import AuthSession
from auth_test.entities.session.value_objects import SessionId
from auth_test.entities.user.value_objects import UserId


class InMemorySessionRepository(ISessionRepository):
    def __init__(self, storage: InMemoryStorage) -> None:
        self._storage = storage

    async def add(self, session: AuthSession) -> AuthSession:
        session_id = SessionId(self._storage.next_id("session"))
        stored = replace(session, id=session_id)
        self._storage.sessions[session_id] = stored
        return stored

    async def get_by_jti(self, jti: str) -> AuthSession | None:
        for session in self._storage.sessions.values():
            if session.jti == jti:
                return session
        return None

    async def revoke(self, jti: str) -> None:
        for session_id, session in self._storage.sessions.items():
            if session.jti == jti:
                self._storage.sessions[session_id] = replace(session, revoked=True)

    async def revoke_all_for_user(self, user_id: UserId) -> None:
        for session_id, session in self._storage.sessions.items():
            if int(session.user_id) == int(user_id):
                self._storage.sessions[session_id] = replace(session, revoked=True)
