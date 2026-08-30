from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from users_service.adapter.database.seed import create_schema, seed_demo_data
from users_service.dependency_injection import Container
from users_service.infrastructure.api.csrf_middleware import CsrfMiddleware
from users_service.infrastructure.api.exc_handlers import map_exc_handlers
from users_service.infrastructure.api.routers import WIRED_MODULES, router
from users_service.infrastructure.api.visitor_middleware import VisitorMiddleware
from users_service.infrastructure.config import Config


def setup_configs() -> Config:
    return Config()


def setup_container() -> Container:
    container = Container()
    container.wire(modules=WIRED_MODULES)
    return container


def setup_routes(app: FastAPI, /) -> None:
    app.include_router(router)


def setup_exc_handlers(app: FastAPI, /) -> None:
    map_exc_handlers(app)


def setup_middleware(app: FastAPI, config: Config, /) -> None:
    """Install the middleware a cookie-authenticated browser frontend needs.

    CORS must name the frontend's origins explicitly: a wildcard is not allowed
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
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepare the schema/demo data on startup, release resources on shutdown."""
    container: Container = app.state.container
    config: Config = container.config()

    engine = container.engine()
    await create_schema(engine)
    if config.SEED_ON_STARTUP:
        await seed_demo_data(engine, container.password_hasher())

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
    setup_routes(app)

    return app


def run() -> None:
    """Start the API server."""
    config = setup_configs()
    uvicorn.run(
        "users_service.bootstrap:bootstrap",
        factory=True,
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )
