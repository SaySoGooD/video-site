from fastapi import APIRouter

from users_service.infrastructure.api.routers import admin, auth, health, users

WIRED_MODULES = [
    "users_service.infrastructure.api.routers.auth",
    "users_service.infrastructure.api.routers.users",
    "users_service.infrastructure.api.routers.admin",
]

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(admin.router)

__all__ = ["router", "WIRED_MODULES"]
