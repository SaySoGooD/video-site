from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewayConfig(BaseSettings):
    """Gateway configuration, loaded from environment / ``.env``.

    Prefixed with ``GATEWAY_`` so one ``.env`` can hold the settings of every
    service in this repository without them colliding.
    """

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    TITLE: str = "Video Site Gateway"
    VERSION: str = "0.1.0"

    # Where the versioned API lives, on the way in and on the way out.
    API_PREFIX: str = "/api/v1"

    USERS_SERVICE_URL: str = "http://localhost:8001"
    # Optional until the service exists; routes to it answer 503 while it does not.
    CONTENT_SERVICE_URL: str | None = None

    # A request that a service has not answered in this long is reported as 504
    # rather than held open — a slow upstream must not exhaust the gateway.
    REQUEST_TIMEOUT_SECONDS: float = 30.0
    CONNECT_TIMEOUT_SECONDS: float = 5.0

    # The browser id users-service issues. The gateway forwards it downstream
    # for every request, logged in or not — an anonymous visitor is exactly the
    # case analytics cares about.
    VISITOR_COOKIE_NAME: str = "visitor_id"

    # Browser frontends live on another origin; credentialed CORS needs them
    # listed explicitly (no wildcard allowed with cookies).
    CORS_ORIGINS: list[str] = []

    # Behind a load balancer the peer address is the balancer, so the real
    # client IP has to be read from X-Forwarded-For. Only enable when a trusted
    # proxy sets it — otherwise a client can forge its own address.
    TRUST_PROXY_HEADERS: bool = False

    model_config = SettingsConfigDict(
        env_prefix="GATEWAY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
