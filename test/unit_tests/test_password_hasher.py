from auth_test.adapter.security.password_hasher import PBKDF2PasswordHasher


class TestPBKDF2PasswordHasher:
    def test_hash_is_not_plaintext_and_verifies(self) -> None:
        hasher = PBKDF2PasswordHasher(iterations=1000)
        digest = hasher.hash("s3cret")

        assert "s3cret" not in digest
        assert hasher.verify("s3cret", digest)
        assert not hasher.verify("wrong", digest)

    def test_hash_is_salted(self) -> None:
        hasher = PBKDF2PasswordHasher(iterations=1000)
        assert hasher.hash("same") != hasher.hash("same")

    def test_malformed_hash_does_not_verify(self) -> None:
        hasher = PBKDF2PasswordHasher(iterations=1000)
        assert not hasher.verify("whatever", "not-a-valid-hash")
