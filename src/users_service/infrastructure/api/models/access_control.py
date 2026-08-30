from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource: str
    action: str
    description: str | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    permissions: list[PermissionResponse] = Field(default_factory=list)


class CreateRoleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class CreatePermissionRequest(BaseModel):
    resource: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class RolePermissionRequest(BaseModel):
    permission_id: int


class UserRoleRequest(BaseModel):
    role_id: int
