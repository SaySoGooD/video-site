from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from users_service.dependency_injection import Container

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: the process is up and serving. No dependencies touched."""
    return {"status": "ok"}


@router.get("/health/ready")
@inject
async def readiness(
    request: Request,
    engine: AsyncEngine = Depends(Provide[Container.engine]),
) -> JSONResponse:
    """Readiness: can this instance actually serve traffic?

    Distinct from liveness on purpose. A process with a dead database should
    be taken out of the load balancer (503) but not restarted in a loop, and
    an orchestrator can only tell the two apart if the endpoints do.
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": str(exc)},
        )

    return JSONResponse(status_code=200, content={"status": "ready"})
