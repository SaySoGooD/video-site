from pydantic import BaseModel


class BusinessItem(BaseModel):
    """A mock business object (no dedicated table — demo only)."""

    id: int
    title: str
    owner: str


class BusinessListResponse(BaseModel):
    resource: str
    items: list[BusinessItem]
