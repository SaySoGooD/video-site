"""The browser-facing half of authentication: HttpOnly cookies + CSRF."""

from conftest import API, browser_login, csrf_header
from fastapi.testclient import TestClient


class TestCookieSession:
    def test_login_sets_httponly_cookies_and_hides_tokens(
        self, browser: TestClient
    ) -> None:
        response = browser.post(
            f"{API}/auth/login",
            json={"email": "viewer@example.com", "password": "viewer123"},
        )
        assert response.status_code == 200, response.text

        body = response.json()
        assert body["tokens"] is None, "tokens must not reach a browser as JSON"
        assert body["csrf_token"]
        assert body["user"]["email"] == "viewer@example.com"

        assert "access_token" in browser.cookies
        assert "refresh_token" in browser.cookies
        set_cookies = response.headers.get_list("set-cookie")
        access_cookie = next(c for c in set_cookies if c.startswith("access_token="))
        assert "HttpOnly" in access_cookie

    def test_me_works_without_any_header(self, browser: TestClient) -> None:
        browser_login(browser, "viewer@example.com", "viewer123")
        response = browser.get(f"{API}/auth/me")
        assert response.status_code == 200
        assert response.json()["username"] == "viewer"

    def test_refresh_uses_the_cookie(self, browser: TestClient) -> None:
        csrf = browser_login(browser, "viewer@example.com", "viewer123")
        response = browser.post(f"{API}/auth/refresh", headers=csrf)
        assert response.status_code == 200, response.text
        assert response.json()["tokens"] is None
        assert browser.get(f"{API}/auth/me").status_code == 200

    def test_logout_clears_the_cookies(self, browser: TestClient) -> None:
        csrf = browser_login(browser, "viewer@example.com", "viewer123")
        assert browser.post(f"{API}/auth/logout", headers=csrf).status_code == 204
        assert "access_token" not in browser.cookies
        assert browser.get(f"{API}/auth/me").status_code == 401


class TestCsrfProtection:
    def test_write_without_csrf_header_is_403(self, browser: TestClient) -> None:
        browser_login(browser, "viewer@example.com", "viewer123")
        response = browser.patch(f"{API}/users/me", json={"display_name": "Nope"})
        assert response.status_code == 403

    def test_write_with_wrong_csrf_header_is_403(self, browser: TestClient) -> None:
        browser_login(browser, "viewer@example.com", "viewer123")
        response = browser.patch(
            f"{API}/users/me",
            headers=csrf_header("not-the-token"),
            json={"display_name": "Nope"},
        )
        assert response.status_code == 403

    def test_write_with_matching_csrf_header_succeeds(
        self, browser: TestClient
    ) -> None:
        csrf = browser_login(browser, "viewer@example.com", "viewer123")
        response = browser.patch(
            f"{API}/users/me", headers=csrf, json={"display_name": "Vic the Second"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["display_name"] == "Vic the Second"

    def test_reads_need_no_csrf_header(self, browser: TestClient) -> None:
        browser_login(browser, "viewer@example.com", "viewer123")
        assert browser.get(f"{API}/auth/me").status_code == 200

    def test_first_login_needs_no_csrf_header(self, browser: TestClient) -> None:
        response = browser.post(
            f"{API}/auth/login",
            json={"email": "viewer@example.com", "password": "viewer123"},
        )
        assert response.status_code == 200
