import re
from collections.abc import Iterator

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from users_service.bootstrap import bootstrap

API = "/api/v1"


class RecordingEmailSender:
    """Captures outgoing mail so tests can read the links out of it.

    Stands in for the console/SMTP senders; it is the only way a test can get
    at a verification or reset token, exactly like a real user reading their
    inbox.
    """

    def __init__(self) -> None:
        self.messages: list[object] = []

    async def send(self, message: object) -> None:
        self.messages.append(message)

    def last_token(self) -> str:
        assert self.messages, "no email was sent"
        body = self.messages[-1].body  # type: ignore[attr-defined]
        match = re.search(r"token=([\w\-]+)", body)
        assert match is not None, f"no token in email body: {body}"
        return match.group(1)

    def last_to(self) -> str:
        assert self.messages, "no email was sent"
        return self.messages[-1].to  # type: ignore[attr-defined]


def _build_client() -> TestClient:
    """Wire the real stack onto a throwaway in-memory SQLite database.

    Only the ``engine`` provider is overridden, so the DI container, unit of
    work, repositories, use cases and routers all stay in play while the test
    run avoids depending on a PostgreSQL server. Entering the client's context
    triggers the lifespan hook, which creates the schema and seeds demo data.
    """
    app = bootstrap()
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    app.state.container.engine.override(providers.Object(engine))
    return TestClient(app)


def _with_mailbox(client: TestClient) -> RecordingEmailSender:
    mailbox = RecordingEmailSender()
    client.app.state.container.email_sender.override(  # type: ignore[attr-defined]
        providers.Object(mailbox)
    )
    return mailbox


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Token mode: tokens come back in the body, sent as bearer headers."""
    monkeypatch.setenv("COOKIE_AUTH_ENABLED", "false")
    test_client = _build_client()
    _with_mailbox(test_client)
    with test_client as started:
        yield started


@pytest.fixture
def mailbox(client: TestClient) -> RecordingEmailSender:
    """The outbox of the ``client`` fixture."""
    return client.app.state.container.email_sender()  # type: ignore[attr-defined]


@pytest.fixture
def browser(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Cookie mode, as a real browser frontend would use the service.

    ``COOKIE_SECURE`` is off because the test client speaks plain HTTP and
    would otherwise drop every ``Secure`` cookie.
    """
    monkeypatch.setenv("COOKIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    test_client = _build_client()
    _with_mailbox(test_client)
    with test_client as started:
        yield started


def login(client: TestClient, email: str, password: str) -> str:
    """Log in (token mode) and return the access token."""
    response = client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["tokens"]["access_token"]


def login_pair(client: TestClient, email: str, password: str) -> tuple[str, str]:
    """Log in (token mode) and return the access + refresh pair."""
    response = client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    tokens = response.json()["tokens"]
    return tokens["access_token"], tokens["refresh_token"]


def browser_login(client: TestClient, email: str, password: str) -> dict[str, str]:
    """Log in (cookie mode) and return the CSRF header to send with writes."""
    response = client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return csrf_header(response.json()["csrf_token"])


def csrf_header(token: str) -> dict[str, str]:
    return {"X-CSRF-Token": token}


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(
    client: TestClient,
    email: str,
    username: str,
    password: str = "password123",
    **extra: object,
) -> dict[str, object]:
    """Register an account and return the created profile."""
    response = client.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "password_repeat": password,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
