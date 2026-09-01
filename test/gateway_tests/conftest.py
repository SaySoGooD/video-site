"""Gateway tests run against the *real* users-service, in the same process.

The gateway's HTTP client is pointed at ASGI transports instead of sockets, so
a request travels the whole way — gateway route matching, identity lookup,
header rewriting, streaming — into the actual users-service app and back. A
mocked upstream would prove the gateway talks to something; this proves it
talks to the service it will be deployed with.
"""

from collections.abc import Iterator

import httpx
import pytest
from dependency_injector import providers
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from gateway.bootstrap import bootstrap as gateway_bootstrap
from gateway.identity import IdentityResolver
from gateway.routes import build_routes
from users_service.bootstrap import bootstrap as users_bootstrap

API = "/api/v1"
USERS_URL = "http://users-service"
CONTENT_URL = "http://content-service"


def build_users_app() -> FastAPI:
    """The real users-service on a throwaway in-memory database."""
    app = users_bootstrap()
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    app.state.container.engine.override(providers.Object(engine))
    return app


def build_echo_app() -> FastAPI:
    """A stand-in for a service behind the gateway.

    It answers with the headers it received, which is how a test can see what
    the gateway decided to say about the caller.
    """
    app = FastAPI()

    @app.api_route(
        "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
    )
    async def echo(request: Request, path: str) -> dict[str, object]:
        return {
            "path": "/" + path,
            "method": request.method,
            "headers": {k.lower(): v for k, v in request.headers.items()},
            "query": dict(request.query_params),
            "body": (await request.body()).decode() or None,
        }

    return app


@pytest.fixture(autouse=True)
def _plain_http_cookies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let the test client keep the cookies users-service sets.

    Autouse, because it has to run *before* the upstream app is built: the
    middleware reads its configuration at startup, so a Secure flag decided
    then cannot be undone later, and httpx drops Secure cookies over http.
    """
    monkeypatch.setenv("COOKIE_SECURE", "false")


@pytest.fixture
def upstreams() -> dict[str, FastAPI]:
    return {"users": build_users_app(), "content": build_echo_app()}


def build_gateway(
    upstreams: dict[str, FastAPI],
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_content: bool = True,
) -> TestClient:
    """A gateway whose client dispatches into the given ASGI apps."""
    monkeypatch.setenv("GATEWAY_USERS_SERVICE_URL", USERS_URL)
    if with_content:
        monkeypatch.setenv("GATEWAY_CONTENT_SERVICE_URL", CONTENT_URL)
    else:
        monkeypatch.delenv("GATEWAY_CONTENT_SERVICE_URL", raising=False)

    app = gateway_bootstrap()
    mounts: dict[str, httpx.AsyncBaseTransport] = {
        USERS_URL: httpx.ASGITransport(app=upstreams["users"]),
    }
    if with_content:
        mounts[CONTENT_URL] = httpx.ASGITransport(app=upstreams["content"])

    client = httpx.AsyncClient(mounts=mounts)
    app.state.client = client
    app.state.routes = build_routes(app.state.config)
    app.state.identity_resolver = IdentityResolver(
        client, app.state.config.USERS_SERVICE_URL, app.state.config.API_PREFIX
    )
    return TestClient(app)


@pytest.fixture
def gateway(
    upstreams: dict[str, FastAPI], monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """Gateway in front of users-service and the echo service."""
    monkeypatch.setenv("COOKIE_AUTH_ENABLED", "false")
    with TestClient(upstreams["users"]):  # runs the lifespan: schema + demo data
        with build_gateway(upstreams, monkeypatch) as client:
            yield client


@pytest.fixture
def browser_gateway(
    upstreams: dict[str, FastAPI], monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """The same, with users-service in cookie mode."""
    monkeypatch.setenv("COOKIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    with TestClient(upstreams["users"]):
        with build_gateway(upstreams, monkeypatch) as client:
            yield client


def gateway_login(client: TestClient, email: str, password: str) -> str:
    """Log in through the gateway (token mode) and return the access token."""
    response = client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["tokens"]["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
