import pytest

from users_service.infrastructure.config import Config

SAFE_SECRET = "a" * 48


def _production_env(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> None:
    """A production configuration that passes, before a test breaks one thing."""
    env = {
        "ENVIRONMENT": "production",
        "JWT_SECRET": SAFE_SECRET,
        "COOKIE_SECURE": "true",
        "CSRF_PROTECTION": "true",
        "EMAIL_BACKEND": "smtp",
        "RATE_LIMIT_ENABLED": "true",
        "REDIS_URL": "redis://localhost:6379/0",
        "SEED_ON_STARTUP": "false",
    }
    env.update(overrides)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


class TestProductionSafety:
    def test_a_correct_production_config_loads(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _production_env(monkeypatch)
        assert Config().is_production

    def test_development_defaults_are_left_alone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENVIRONMENT", "development")
        config = Config()
        assert not config.is_production
        assert config.EMAIL_BACKEND == "console"

    @pytest.mark.parametrize(
        ("override", "expected"),
        [
            ({"JWT_SECRET": "change_me_to_a_long_random_secret"}, "JWT_SECRET"),
            ({"JWT_SECRET": "too-short"}, "32 characters"),
            ({"COOKIE_SECURE": "false"}, "COOKIE_SECURE"),
            ({"CSRF_PROTECTION": "false"}, "CSRF_PROTECTION"),
            ({"EMAIL_BACKEND": "console"}, "EMAIL_BACKEND"),
            ({"RATE_LIMIT_ENABLED": "false"}, "RATE_LIMIT_ENABLED"),
            ({"REDIS_URL": ""}, "REDIS_URL"),
            ({"SEED_ON_STARTUP": "true"}, "SEED_ON_STARTUP"),
        ],
    )
    def test_unsafe_settings_refuse_to_start(
        self,
        monkeypatch: pytest.MonkeyPatch,
        override: dict[str, str],
        expected: str,
    ) -> None:
        _production_env(monkeypatch, **override)

        with pytest.raises(ValueError, match=expected):
            Config()


class TestRateLimitPolicies:
    def test_disabling_rate_limiting_zeroes_every_policy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        config = Config()

        assert not config.login_ip_policy.is_enforced
        assert not config.login_account_policy.is_enforced
        assert not config.register_ip_policy.is_enforced
        assert not config.forgot_password_email_policy.is_enforced

    def test_policies_carry_the_configured_numbers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOGIN_MAX_ATTEMPTS_PER_ACCOUNT", "7")
        monkeypatch.setenv("LOGIN_WINDOW_SECONDS", "120")
        config = Config()

        assert config.login_account_policy.limit == 7
        assert config.login_account_policy.window_seconds == 120
