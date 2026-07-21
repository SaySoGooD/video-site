from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration, loaded from environment / ``.env``."""

    # True -> in-memory mock DB (no server needed); False -> PostgreSQL.
    MOCK_DB: bool = True

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "auth_test"

    JWT_SECRET: str = "change_me_to_a_long_random_secret"
    JWT_ALGORITHM: str = "HS256"
    # Short-lived access token; long-lived refresh token (7 days).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Password hashing scheme: "argon2" or "pbkdf2".
    PASSWORD_HASHER: str = "argon2"

    # Optional Redis cache. Empty -> no-op cache (Redis not required).
    REDIS_URL: str | None = None
    AUTH_CACHE_TTL_SECONDS: int = 30

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    API_TITLE: str = "Auth Test API"
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
