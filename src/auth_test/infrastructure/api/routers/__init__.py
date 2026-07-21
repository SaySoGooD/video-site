from fastapi import APIRouter

from auth_test.infrastructure.api.routers import admin, auth, business, health

WIRED_MODULES = [
    "auth_test.infrastructure.api.routers.auth",
    "auth_test.infrastructure.api.routers.admin",
]

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(admin.router)
router.include_router(business.router)

__all__ = ["router", "WIRED_MODULES"]
