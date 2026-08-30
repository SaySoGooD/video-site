import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from users_service.adapter.database.seed import create_schema, seed_demo_data
from users_service.dependency_injection import Container
from users_service.infrastructure.api.csrf_middleware import CsrfMiddleware
from users_service.infrastructure.api.exc_handlers import map_exc_handlers
from users_service.infrastructure.api.routers import (
    WIRED_MODULES,
    api_router,
    health_router,
)
from users_service.infrastructure.api.visitor_middleware import VisitorMiddleware
from users_service.infrastructure.config import Config

logger = logging.getLogger(__name__)


def setup_configs() -> Config:
    return Config()


def setup_container() -> Container:
    container = Container()
    container.wire(modules=WIRED_MODULES)
    return container


def setup_routes(app: FastAPI, config: Config, /) -> None:
    app.include_router(health_router)
    app.include_router(api_router, prefix=config.API_PREFIX)


def setup_exc_handlers(app: FastAPI, /) -> None:
    map_exc_handlers(app)


def setup_middleware(app: FastAPI, config: Config, /) -> None:
    """Install the middleware a cookie-authenticated browser frontend needs.

    CORS must name the frontend origins explicitly: a wildcard is not allowed
    together with credentials, and cookies are exactly that.
    """
    app.add_middleware(CsrfMiddleware, config=config)
    app.add_middleware(VisitorMiddleware, config=config)

    if config.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["Retry-After"],
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepare the database on startup, release resources on shutdown.

    ``SEED_ON_STARTUP`` creates the schema and demo data for a local run. In
    production it is refused by the config validator: Alembic owns the schema
    there, and two things creating tables is how drift starts.
    """
    container: Container = app.state.container
    config: Config = container.config()

    engine = container.engine()
    if config.SEED_ON_STARTUP:
        await create_schema(engine)
        await seed_demo_data(engine, container.password_hasher())
    else:
        logger.info("SEED_ON_STARTUP is off; expecting Alembic-managed schema")

    yield

    await engine.dispose()


def bootstrap() -> FastAPI:
    """Assemble the application: config, DI container, FastAPI app."""
    config = setup_configs()
    container = setup_container()

    app = FastAPI(
        title=config.API_TITLE,
        version=config.API_VERSION,
        lifespan=lifespan,
    )
    app.state.container = container

    setup_exc_handlers(app)
    setup_middleware(app, config)
    setup_routes(app, config)

    return app


def run() -> None:
    """Start the API server."""
    config = setup_configs()
    uvicorn.run(
        "users_service.bootstrap:bootstrap",
        factory=True,
        host=config.API_HOST,
        port=config.API_PORT,
        reload=not config.is_production,
    )
