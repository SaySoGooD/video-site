from users_service.adapter.security.argon2_password_hasher import (
    Argon2PasswordHasher,
)


class TestArgon2PasswordHasher:
    def test_hash_is_argon2_and_verifies(self) -> None:
        hasher = Argon2PasswordHasher()
        digest = hasher.hash("s3cret")

        assert digest.startswith("$argon2")
        assert "s3cret" not in digest
        assert hasher.verify("s3cret", digest)
        assert not hasher.verify("wrong", digest)

    def test_hash_is_salted(self) -> None:
        hasher = Argon2PasswordHasher()
        assert hasher.hash("same") != hasher.hash("same")

    def test_malformed_hash_does_not_verify(self) -> None:
        assert not Argon2PasswordHasher().verify("whatever", "not-a-valid-hash")
