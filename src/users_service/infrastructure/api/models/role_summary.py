from pydantic import BaseModel, ConfigDict


class RoleSummary(BaseModel):
    """A role as it appears on a user's own profile (no permission list)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
