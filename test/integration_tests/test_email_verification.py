from conftest import API, RecordingEmailSender, auth_header, login, register
from fastapi.testclient import TestClient


class TestEmailVerification:
    def test_registration_mails_a_link_and_leaves_account_unverified(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        created = register(client, "fresh@example.com", "freshuser")

        assert created["email_verified"] is False
        assert created["email_verified_at"] is None
        assert mailbox.last_to() == "fresh@example.com"

    def test_token_verifies_the_account(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        register(client, "verify@example.com", "verifyme")
        token = mailbox.last_token()

        response = client.get(f"{API}/auth/verify-email", params={"token": token})
        assert response.status_code == 200, response.text
        assert response.json()["email_verified"] is True
        assert response.json()["email_verified_at"] is not None

    def test_token_cannot_be_used_twice(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        register(client, "once@example.com", "onceuser")
        token = mailbox.last_token()

        assert (
            client.get(
                f"{API}/auth/verify-email", params={"token": token}
            ).status_code
            == 200
        )
        replay = client.get(f"{API}/auth/verify-email", params={"token": token})
        assert replay.status_code == 400

    def test_unknown_token_is_400(self, client: TestClient) -> None:
        response = client.get(
            f"{API}/auth/verify-email", params={"token": "not-a-real-token"}
        )
        assert response.status_code == 400

    def test_plaintext_token_is_not_stored(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        """The database must hold only the hash of what was mailed."""
        import asyncio

        from sqlalchemy import text

        register(client, "hashed@example.com", "hasheduser")
        token = mailbox.last_token()
        engine = client.app.state.container.engine()  # type: ignore[attr-defined]

        async def stored_hashes() -> list[str]:
            async with engine.connect() as connection:
                result = await connection.execute(
                    text("SELECT token_hash FROM security_tokens")
                )
                return [row[0] for row in result]

        hashes = asyncio.run(stored_hashes())
        assert hashes
        assert token not in hashes

    def test_changing_email_unverifies_and_remails(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        register(client, "mover@example.com", "moveruser")
        token = mailbox.last_token()
        client.get(f"{API}/auth/verify-email", params={"token": token})

        headers = auth_header(login(client, "mover@example.com", "password123"))
        response = client.patch(
            f"{API}/users/me", headers=headers, json={"email": "moved@example.com"}
        )

        assert response.status_code == 200, response.text
        assert response.json()["email"] == "moved@example.com"
        assert response.json()["email_verified"] is False
        assert mailbox.last_to() == "moved@example.com"

    def test_issuing_a_new_link_invalidates_the_previous_one(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        register(client, "reissue@example.com", "reissueuser")
        first_token = mailbox.last_token()

        headers = auth_header(login(client, "reissue@example.com", "password123"))
        client.patch(
            f"{API}/users/me",
            headers=headers,
            json={"email": "reissued@example.com"},
        )
        second_token = mailbox.last_token()

        assert first_token != second_token
        stale = client.get(
            f"{API}/auth/verify-email", params={"token": first_token}
        )
        assert stale.status_code == 400
        fresh = client.get(
            f"{API}/auth/verify-email", params={"token": second_token}
        )
        assert fresh.status_code == 200
