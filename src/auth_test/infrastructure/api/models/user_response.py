from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from auth_test.infrastructure.api.models.auth import RoleSummary


class UserResponse(BaseModel):
    """Public view of a user account."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime | None = None
    roles: list[RoleSummary] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
