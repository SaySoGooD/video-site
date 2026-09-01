from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gateway.config import GatewayConfig
from gateway.gateway_router import router as proxy_router
from gateway.identity import IdentityResolver
from gateway.routes import build_routes


def setup_config() -> GatewayConfig:
    return GatewayConfig()


def build_client(config: GatewayConfig) -> httpx.AsyncClient:
    """One connection pool for the whole process.

    Redirects are not followed: a service answering 302 is telling the *client*
    something, and the gateway silently chasing it would hide that.
    """
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            config.REQUEST_TIMEOUT_SECONDS,
            connect=config.CONNECT_TIMEOUT_SECONDS,
        ),
        follow_redirects=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.client.aclose()


def setup_health(app: FastAPI, config: GatewayConfig, /) -> None:
    """Probes, deliberately outside the versioned prefix.

    Liveness says the process is up. Readiness asks users-service whether *it*
    is ready, because a gateway that cannot reach the service every route
    depends on has nothing useful to offer.
    """

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def readiness() -> JSONResponse:
        url = config.USERS_SERVICE_URL.rstrip("/") + "/health/ready"
        try:
            response = await app.state.client.get(url)
        except httpx.HTTPError as exc:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "users_service": str(exc)},
            )

        if response.status_code != 200:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "users_service": response.status_code,
                },
            )
        return JSONResponse(status_code=200, content={"status": "ready"})


def bootstrap() -> FastAPI:
    """Assemble the gateway: config, HTTP client, routing table, proxy route."""
    config = setup_config()

    app = FastAPI(title=config.TITLE, version=config.VERSION, lifespan=lifespan)
    app.state.config = config
    app.state.client = build_client(config)
    app.state.routes = build_routes(config)
    app.state.identity_resolver = IdentityResolver(
        app.state.client, config.USERS_SERVICE_URL, config.API_PREFIX
    )

    if config.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["Retry-After", "X-Request-Id"],
        )

    setup_health(app, config)
    # Mounted last: the catch-all would otherwise swallow the probes.
    app.include_router(proxy_router, prefix=config.API_PREFIX)

    return app


def run() -> None:
    uvicorn.run(
        "gateway.bootstrap:bootstrap",
        factory=True,
        host=setup_config().HOST,
        port=setup_config().PORT,
        reload=False,
    )
