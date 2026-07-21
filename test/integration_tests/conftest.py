from collections.abc import Iterator

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from auth_test.bootstrap import bootstrap


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A TestClient exercising the SQLAlchemy backend on in-memory SQLite.

    Pins ``MOCK_DB=False`` (the SQLAlchemy path) and overrides only the
    ``engine`` provider, so the whole real stack stays in play (DI container,
    unit of work, repositories, use cases, routers) while avoiding a real
    PostgreSQL dependency in the test run. Entering the client's context
    triggers the lifespan hook, which creates the schema and seeds the demo
    data on this SQLite engine.
    """
    monkeypatch.setenv("MOCK_DB", "false")
    app = bootstrap()
    container = app.state.container

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    container.engine.override(providers.Object(engine))

    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str, password: str) -> str:
    """Log in and return the bearer token."""
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
