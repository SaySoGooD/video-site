from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration, loaded from environment / ``.env``."""

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
    REFRESH_COOKIE_PATH: str = "/auth"

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

    SEED_ON_STARTUP: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy connection URL (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
