"""The visitor id: the one link between "who is this user?" and analytics."""

from conftest import browser_login, register
from fastapi.testclient import TestClient


class TestVisitorCookie:
    def test_issued_to_anonymous_visitors(self, browser: TestClient) -> None:
        response = browser.post(
            "/auth/login",
            json={"email": "viewer@example.com", "password": "wrong"},
        )
        assert response.status_code == 401
        assert browser.cookies.get("visitor_id")

    def test_reused_across_requests(self, browser: TestClient) -> None:
        browser.get("/users/1")
        first = browser.cookies.get("visitor_id")

        browser.get("/users/1")
        assert browser.cookies.get("visitor_id") == first

    def test_recorded_on_the_account_at_signup(self, browser: TestClient) -> None:
        browser.get("/users/1")
        visitor_id = browser.cookies.get("visitor_id")

        created = register(browser, "tracked@example.com", "tracked")
        assert created["visitor_id"] == visitor_id

    def test_not_exposed_on_a_public_profile(self, browser: TestClient) -> None:
        created = register(browser, "private@example.com", "privateguy")
        public = browser.get(f"/users/{created['id']}").json()
        assert "visitor_id" not in public

    def test_visible_to_the_owner_on_auth_me(self, browser: TestClient) -> None:
        register(browser, "owner@example.com", "ownerguy")
        browser_login(browser, "owner@example.com", "password123")

        me = browser.get("/auth/me").json()
        assert me["visitor_id"] == browser.cookies.get("visitor_id")
