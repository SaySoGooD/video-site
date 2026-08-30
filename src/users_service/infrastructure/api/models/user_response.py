from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from users_service.infrastructure.api.models.role_summary import RoleSummary


class UserResponse(BaseModel):
    """The account as its **owner** (or an administrator) sees it.

    Carries private fields — email, verification state, roles, permissions,
    visitor id — so it is only ever returned to the user themselves or to an
    admin endpoint.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    display_name: str | None = None
    is_active: bool
    is_superuser: bool
    email_verified: bool = False
    email_verified_at: datetime | None = None
    visitor_id: str | None = None
    created_at: datetime | None = None
    roles: list[RoleSummary] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
