from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from auth_test.adapter.database.seed import create_schema, seed_demo_data
from auth_test.adapter.memory.seed import seed_memory
from auth_test.dependency_injection import Container
from auth_test.infrastructure.api.exc_handlers import map_exc_handlers
from auth_test.infrastructure.api.routers import WIRED_MODULES, router
from auth_test.infrastructure.config import Config


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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepare the schema/demo data on startup, release resources on shutdown.

    The database backend is chosen by ``config.MOCK_DB`` — ``True`` runs against
    an in-memory mock (no server), ``False`` against PostgreSQL.
    """
    container: Container = app.state.container
    config: Config = container.config()

    if config.MOCK_DB:
        if config.SEED_ON_STARTUP:
            seed_memory(container.memory_storage(), container.password_hasher())
        yield
        return

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
    setup_routes(app)

    return app


def run() -> None:
    """Start the API server."""
    config = setup_configs()
    uvicorn.run(
        "auth_test.bootstrap:bootstrap",
        factory=True,
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )
