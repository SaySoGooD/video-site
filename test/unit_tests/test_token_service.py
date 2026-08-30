import pytest

from users_service.adapter.security.token_service import JwtTokenService
from users_service.application.common.errors import AuthenticationError
from users_service.entities.user.value_objects import UserId


class TestJwtTokenService:
    def test_access_round_trip(self) -> None:
        service = JwtTokenService(secret="test-secret")
        issued = service.issue_access(UserId(42), "jti-abc")

        payload = service.decode(issued.token)
        assert payload.user_id == 42
        assert payload.jti == "jti-abc"
        assert payload.token_type == "access"

    def test_refresh_carries_refresh_type(self) -> None:
        service = JwtTokenService(secret="test-secret")
        issued = service.issue_refresh(UserId(7), "jti-xyz")

        payload = service.decode(issued.token)
        assert payload.token_type == "refresh"
        assert payload.jti == "jti-xyz"

    def test_access_and_refresh_share_the_jti(self) -> None:
        service = JwtTokenService(secret="test-secret")
        access = service.issue_access(UserId(1), "shared")
        refresh = service.issue_refresh(UserId(1), "shared")
        assert service.decode(access.token).jti == service.decode(refresh.token).jti

    def test_wrong_secret_is_rejected(self) -> None:
        issued = JwtTokenService(secret="right").issue_access(UserId(1), "j")
        with pytest.raises(AuthenticationError):
            JwtTokenService(secret="wrong").decode(issued.token)

    def test_garbage_token_is_rejected(self) -> None:
        with pytest.raises(AuthenticationError):
            JwtTokenService(secret="right").decode("not.a.jwt")
