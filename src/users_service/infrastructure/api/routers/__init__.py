from fastapi import APIRouter

from users_service.infrastructure.api.routers import (
    admin,
    auth,
    health,
    moderation,
    users,
)

WIRED_MODULES = [
    "users_service.infrastructure.api.routers.auth",
    "users_service.infrastructure.api.routers.users",
    "users_service.infrastructure.api.routers.admin",
    "users_service.infrastructure.api.routers.moderation",
    "users_service.infrastructure.api.routers.health",
]

# Versioned API surface, mounted under API_PREFIX.
api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
api_router.include_router(moderation.router)

# Probes stay unversioned: an orchestrator should not have to follow API
# versioning to find out whether the process is alive.
health_router = health.router

__all__ = ["api_router", "health_router", "WIRED_MODULES"]
