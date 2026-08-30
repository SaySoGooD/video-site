from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from users_service.application.common.rate_limit_policy import RateLimitPolicy


class Config(BaseSettings):
    """Application configuration, loaded from environment / ``.env``.

    Every secret comes from the environment; nothing sensitive has a usable
    default. ``ENVIRONMENT=production`` turns the loose development defaults
    into hard errors at startup — see :meth:`_check_production_safety`.
    """

    ENVIRONMENT: str = "development"

    # A full SQLAlchemy URL wins over the DB_* parts when set — the shape most
    # hosting platforms hand you, and what lets the migration tests point at a
    # throwaway database.
    DATABASE_URL: str | None = None

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "users_service"

    JWT_SECRET: str = "change_me_to_a_long_random_secret"
    JWT_ALGORITHM: str = "HS256"
    # Short-lived access token; long-lived refresh token (30 days — a video
    # site is a place people come back to, not a banking app).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

    # Password hashing scheme: "argon2" or "pbkdf2".
    PASSWORD_HASHER: str = "argon2"

    # Optional Redis cache. Empty -> no-op cache (Redis not required).
    REDIS_URL: str | None = None
    AUTH_CACHE_TTL_SECONDS: int = 30

    # --- browser session cookies -------------------------------------------
    # A browser frontend never sees the tokens: they are set as HttpOnly
    # cookies, so a XSS payload cannot read them out of localStorage. Set
    # COOKIE_SECURE=False only for plain-HTTP local development.
    COOKIE_AUTH_ENABLED: bool = True
    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    ACCESS_COOKIE_NAME: str = "access_token"
    REFRESH_COOKIE_NAME: str = "refresh_token"
    # The refresh cookie is scoped to the endpoints that need it, so ordinary
    # requests never carry it.
    REFRESH_COOKIE_PATH: str = "/api/v1/auth"

    # Cookie auth means the browser attaches credentials automatically, so
    # state-changing requests are verified with a double-submit CSRF token:
    # a readable cookie the frontend echoes back in a header.
    CSRF_PROTECTION: bool = True
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # --- visitor identity ---------------------------------------------------
    # Long-lived, opaque browser id issued to everyone, logged in or not. It is
    # what lets the analytics service join a visitor's activity to an account
    # once they sign up. Browsers cap cookie lifetime at 400 days.
    VISITOR_COOKIE_NAME: str = "visitor_id"
    VISITOR_COOKIE_MAX_AGE_DAYS: int = 400

    # --- email --------------------------------------------------------------
    # "console" logs the message (development); "smtp" actually sends it.
    EMAIL_BACKEND: str = "console"
    EMAIL_FROM: str = "no-reply@example.com"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True

    # Where the links in those emails point — the frontend, not this API.
    # ``{token}`` is substituted with the one-time secret.
    EMAIL_VERIFICATION_URL: str = "http://localhost:3000/verify-email?token={token}"
    PASSWORD_RESET_URL: str = "http://localhost:3000/reset-password?token={token}"
    EMAIL_VERIFICATION_TTL_HOURS: int = 24
    PASSWORD_RESET_TTL_MINUTES: int = 30

    # --- rate limiting ------------------------------------------------------
    # Limits are per window; set a limit to 0 to disable that rule.
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_MAX_ATTEMPTS_PER_IP: int = 30
    LOGIN_MAX_ATTEMPTS_PER_ACCOUNT: int = 5
    LOGIN_WINDOW_SECONDS: int = 15 * 60
    REGISTER_MAX_PER_IP: int = 10
    REGISTER_WINDOW_SECONDS: int = 60 * 60
    FORGOT_PASSWORD_MAX_PER_EMAIL: int = 3
    FORGOT_PASSWORD_MAX_PER_IP: int = 10
    FORGOT_PASSWORD_WINDOW_SECONDS: int = 60 * 60
    RESET_PASSWORD_MAX_PER_IP: int = 10
    RESET_PASSWORD_WINDOW_SECONDS: int = 60 * 60

    # Role granted to every newly registered account.
    DEFAULT_ROLE_NAME: str = "user"

    # Browser frontends live on another origin; credentialed CORS needs them
    # listed explicitly (no wildcard allowed with cookies).
    CORS_ORIGINS: list[str] = []

    # Behind a gateway/reverse proxy the peer address is the proxy, so the
    # client IP has to be read from X-Forwarded-For. Only enable this when a
    # trusted proxy actually sets that header — otherwise a client can forge it.
    TRUST_PROXY_HEADERS: bool = False

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    API_TITLE: str = "Users Service API"
    API_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"

    # Create tables and demo data at startup. Off in production, where Alembic
    # owns the schema.
    SEED_ON_STARTUP: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy connection URL (asyncpg driver by default)."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def login_ip_policy(self) -> RateLimitPolicy:
        return self._policy(
            self.LOGIN_MAX_ATTEMPTS_PER_IP, self.LOGIN_WINDOW_SECONDS
        )

    @property
    def login_account_policy(self) -> RateLimitPolicy:
        """The per-account limit doubles as the temporary lockout rule."""
        return self._policy(
            self.LOGIN_MAX_ATTEMPTS_PER_ACCOUNT, self.LOGIN_WINDOW_SECONDS
        )

    @property
    def register_ip_policy(self) -> RateLimitPolicy:
        return self._policy(self.REGISTER_MAX_PER_IP, self.REGISTER_WINDOW_SECONDS)

    @property
    def forgot_password_email_policy(self) -> RateLimitPolicy:
        return self._policy(
            self.FORGOT_PASSWORD_MAX_PER_EMAIL,
            self.FORGOT_PASSWORD_WINDOW_SECONDS,
        )

    @property
    def forgot_password_ip_policy(self) -> RateLimitPolicy:
        return self._policy(
            self.FORGOT_PASSWORD_MAX_PER_IP, self.FORGOT_PASSWORD_WINDOW_SECONDS
        )

    @property
    def reset_password_ip_policy(self) -> RateLimitPolicy:
        return self._policy(
            self.RESET_PASSWORD_MAX_PER_IP, self.RESET_PASSWORD_WINDOW_SECONDS
        )

    def _policy(self, limit: int, window_seconds: int) -> RateLimitPolicy:
        return RateLimitPolicy(
            limit=limit if self.RATE_LIMIT_ENABLED else 0,
            window_seconds=window_seconds,
        )

    @model_validator(mode="after")
    def _check_production_safety(self) -> Self:
        """Refuse to start with development defaults in production.

        These are the settings that are harmless locally and dangerous live —
        a shipped JWT secret, cookies without ``Secure``, reset links written
        to the log. Failing at startup is the only reliable way to catch them:
        every one of these is silent at runtime.
        """
        if not self.is_production:
            return self

        problems: list[str] = []
        if self.JWT_SECRET == "change_me_to_a_long_random_secret":
            problems.append("JWT_SECRET is still the default")
        if len(self.JWT_SECRET) < 32:
            problems.append("JWT_SECRET must be at least 32 characters")
        if self.COOKIE_AUTH_ENABLED and not self.COOKIE_SECURE:
            problems.append("COOKIE_SECURE must be true")
        if self.COOKIE_AUTH_ENABLED and not self.CSRF_PROTECTION:
            problems.append("CSRF_PROTECTION must be on with cookie auth")
        if self.EMAIL_BACKEND != "smtp":
            problems.append("EMAIL_BACKEND must be smtp, not console")
        if not self.RATE_LIMIT_ENABLED:
            problems.append("RATE_LIMIT_ENABLED must be true")
        if not self.REDIS_URL:
            problems.append(
                "REDIS_URL must be set so rate limits hold across workers"
            )
        if self.SEED_ON_STARTUP:
            problems.append(
                "SEED_ON_STARTUP must be false (Alembic owns the schema)"
            )

        if problems:
            raise ValueError(
                "Unsafe production configuration: " + "; ".join(problems)
            )
        return self
