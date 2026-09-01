"""What the gateway must get right: routing, identity, headers, failures."""

import httpx
import pytest
from conftest import API, auth_header, build_gateway, gateway_login
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestProbes:
    def test_liveness_needs_no_upstream(self, gateway: TestClient) -> None:
        response = gateway.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_readiness_follows_users_service(self, gateway: TestClient) -> None:
        assert gateway.get("/health/ready").json() == {"status": "ready"}

    def test_probes_are_not_proxied(self, gateway: TestClient) -> None:
        """The catch-all must not swallow the gateway's own endpoints."""
        assert gateway.get("/health").json()["status"] == "ok"


class TestRouting:
    def test_forwards_auth_to_users_service(self, gateway: TestClient) -> None:
        response = gateway.post(
            f"{API}/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["user"]["username"] == "admin"

    def test_forwards_the_authenticated_call(self, gateway: TestClient) -> None:
        token = gateway_login(gateway, "viewer@example.com", "viewer123")

        response = gateway.get(f"{API}/users/me", headers=auth_header(token))

        assert response.status_code == 200
        assert response.json()["email"] == "viewer@example.com"

    def test_passes_query_parameters_through(self, gateway: TestClient) -> None:
        response = gateway.get(
            f"{API}/content/videos", params={"page": "2", "tag": "cats"}
        )
        assert response.status_code == 200
        assert response.json()["query"] == {"page": "2", "tag": "cats"}

    def test_passes_the_body_and_method_through(self, gateway: TestClient) -> None:
        response = gateway.post(f"{API}/content/videos", json={"title": "Clip"})

        body = response.json()
        assert body["method"] == "POST"
        assert body["body"] == '{"title":"Clip"}'

    def test_upstream_status_codes_are_preserved(
        self, gateway: TestClient
    ) -> None:
        response = gateway.get(f"{API}/users/424242")
        assert response.status_code == 404

    def test_unknown_prefix_is_404(self, gateway: TestClient) -> None:
        assert gateway.get(f"{API}/nonsense/thing").status_code == 404

    def test_a_service_that_is_not_deployed_is_503(
        self, upstreams: dict[str, FastAPI], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COOKIE_AUTH_ENABLED", "false")
        with TestClient(upstreams["users"]):
            with build_gateway(upstreams, monkeypatch, with_content=False) as client:
                response = client.get(f"{API}/content/videos")

        assert response.status_code == 503
        assert "content" in response.json()["detail"]


class TestIdentity:
    def test_anonymous_requests_carry_no_identity(
        self, gateway: TestClient
    ) -> None:
        headers = gateway.get(f"{API}/content/videos").json()["headers"]
        assert "x-user-id" not in headers

    def test_a_logged_in_caller_is_announced_downstream(
        self, gateway: TestClient
    ) -> None:
        token = gateway_login(gateway, "viewer@example.com", "viewer123")

        headers = gateway.get(
            f"{API}/content/videos", headers=auth_header(token)
        ).json()["headers"]

        assert headers["x-user-username"] == "viewer"
        assert int(headers["x-user-id"]) > 0
        assert "content.read" in headers["x-user-permissions"]
        assert headers["x-user-superuser"] == "false"

    def test_superuser_is_marked(self, gateway: TestClient) -> None:
        token = gateway_login(gateway, "admin@example.com", "admin123")

        headers = gateway.get(
            f"{API}/content/videos", headers=auth_header(token)
        ).json()["headers"]

        assert headers["x-user-superuser"] == "true"

    def test_client_supplied_identity_headers_are_stripped(
        self, gateway: TestClient
    ) -> None:
        """Anyone could send X-User-Id: 1. Nobody may be believed for it."""
        headers = gateway.get(
            f"{API}/content/videos",
            headers={
                "X-User-Id": "1",
                "X-User-Permissions": "users.manage",
                "X-User-Superuser": "true",
            },
        ).json()["headers"]

        assert "x-user-id" not in headers
        assert "x-user-permissions" not in headers
        assert "x-user-superuser" not in headers

    def test_a_forged_header_cannot_survive_a_real_login(
        self, gateway: TestClient
    ) -> None:
        token = gateway_login(gateway, "viewer@example.com", "viewer123")

        headers = gateway.get(
            f"{API}/content/videos",
            headers={**auth_header(token), "X-User-Superuser": "true"},
        ).json()["headers"]

        # The gateway's own answer wins over whatever the client claimed.
        assert headers["x-user-superuser"] == "false"
        assert headers["x-user-username"] == "viewer"

    def test_a_revoked_session_stops_working_at_once(
        self, gateway: TestClient
    ) -> None:
        """The reason identity is resolved per request rather than from the JWT."""
        token = gateway_login(gateway, "viewer@example.com", "viewer123")
        assert (
            "x-user-id"
            in gateway.get(
                f"{API}/content/videos", headers=auth_header(token)
            ).json()["headers"]
        )

        gateway.post(f"{API}/auth/logout", headers=auth_header(token))

        headers = gateway.get(
            f"{API}/content/videos", headers=auth_header(token)
        ).json()["headers"]
        assert "x-user-id" not in headers

    def test_visitor_id_is_forwarded(self, browser_gateway: TestClient) -> None:
        browser_gateway.post(
            f"{API}/auth/login",
            json={"email": "viewer@example.com", "password": "viewer123"},
        )

        headers = browser_gateway.get(f"{API}/content/videos").json()["headers"]
        assert headers["x-visitor-id"] == browser_gateway.cookies.get("visitor_id")


class TestHeaders:
    def test_set_cookie_headers_all_survive(
        self, browser_gateway: TestClient
    ) -> None:
        """Login sets access, refresh and CSRF cookies — all three must arrive."""
        response = browser_gateway.post(
            f"{API}/auth/login",
            json={"email": "viewer@example.com", "password": "viewer123"},
        )

        names = {
            cookie.split("=", 1)[0]
            for cookie in response.headers.get_list("set-cookie")
        }
        assert {"access_token", "refresh_token", "csrf_token"} <= names

    def test_cookies_authenticate_through_the_gateway(
        self, browser_gateway: TestClient
    ) -> None:
        browser_gateway.post(
            f"{API}/auth/login",
            json={"email": "viewer@example.com", "password": "viewer123"},
        )

        response = browser_gateway.get(f"{API}/users/me")
        assert response.status_code == 200
        assert response.json()["username"] == "viewer"

    def test_a_request_id_is_added(self, gateway: TestClient) -> None:
        headers = gateway.get(f"{API}/content/videos").json()["headers"]
        assert headers["x-request-id"]

    def test_an_existing_request_id_is_kept(self, gateway: TestClient) -> None:
        headers = gateway.get(
            f"{API}/content/videos", headers={"X-Request-Id": "trace-me"}
        ).json()["headers"]
        assert headers["x-request-id"] == "trace-me"

    def test_forwarded_headers_describe_the_caller(
        self, gateway: TestClient
    ) -> None:
        headers = gateway.get(f"{API}/content/videos").json()["headers"]
        assert headers["x-forwarded-for"]
        assert headers["x-forwarded-proto"] == "http"

    def test_retry_after_is_passed_through(self, gateway: TestClient) -> None:
        """A 429 from users-service must reach the client with its hint intact."""
        for _ in range(6):
            response = gateway.post(
                f"{API}/auth/login",
                json={"email": "viewer@example.com", "password": "wrong"},
            )

        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) > 0


class TestUpstreamFailures:
    @staticmethod
    def _broken_gateway(
        upstreams: dict[str, FastAPI],
        monkeypatch: pytest.MonkeyPatch,
        error: Exception,
    ) -> TestClient:
        client = build_gateway(upstreams, monkeypatch)

        def fail(request: httpx.Request) -> httpx.Response:
            raise error

        app = client.app
        app.state.client = httpx.AsyncClient(  # type: ignore[attr-defined]
            transport=httpx.MockTransport(fail)
        )
        return client

    def test_unreachable_upstream_is_502(
        self, upstreams: dict[str, FastAPI], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COOKIE_AUTH_ENABLED", "false")
        client = self._broken_gateway(
            upstreams, monkeypatch, httpx.ConnectError("refused")
        )

        with client:
            response = client.get(f"{API}/users/1")

        assert response.status_code == 502

    def test_a_slow_upstream_is_504(
        self, upstreams: dict[str, FastAPI], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COOKIE_AUTH_ENABLED", "false")
        client = self._broken_gateway(
            upstreams, monkeypatch, httpx.ReadTimeout("too slow")
        )

        with client:
            response = client.get(f"{API}/users/1")

        assert response.status_code == 504
