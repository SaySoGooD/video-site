"""Mock business endpoints — no dedicated tables, just protected views.

Each route depends on a specific ``resource:action`` permission. The system
answers uniformly: 200 with data if the user is allowed, 401 if the request
cannot be tied to a logged-in user, 403 if the user is known but lacks the
permission. These are the "fictional business objects" the access-control
system is demonstrated against.
"""

from fastapi import APIRouter, Depends

from auth_test.entities.user.models import User
from auth_test.infrastructure.api.dependencies import require_permission
from auth_test.infrastructure.api.models.business import (
    BusinessItem,
    BusinessListResponse,
)

router = APIRouter(tags=["business objects (mock)"])

_DOCUMENTS = [
    BusinessItem(id=1, title="Q3 Strategy", owner="alice@example.com"),
    BusinessItem(id=2, title="Onboarding Guide", owner="ed@example.com"),
    BusinessItem(id=3, title="Security Policy", owner="alice@example.com"),
]

_REPORTS = [
    BusinessItem(id=101, title="Monthly Revenue", owner="alice@example.com"),
    BusinessItem(id=102, title="Active Users", owner="vic@example.com"),
]


@router.get("/documents", response_model=BusinessListResponse)
async def list_documents(
    _: User = Depends(require_permission("document", "read")),
) -> BusinessListResponse:
    return BusinessListResponse(resource="document", items=_DOCUMENTS)


@router.post("/documents", response_model=BusinessItem)
async def create_document(
    _: User = Depends(require_permission("document", "create")),
) -> BusinessItem:
    return BusinessItem(id=4, title="New Document", owner="you@example.com")


@router.put("/documents/{document_id}", response_model=BusinessItem)
async def update_document(
    document_id: int,
    _: User = Depends(require_permission("document", "update")),
) -> BusinessItem:
    return BusinessItem(
        id=document_id, title="Updated Document", owner="you@example.com"
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    _: User = Depends(require_permission("document", "delete")),
) -> dict[str, str]:
    return {"status": "deleted", "id": str(document_id)}


@router.get("/reports", response_model=BusinessListResponse)
async def list_reports(
    _: User = Depends(require_permission("report", "read")),
) -> BusinessListResponse:
    return BusinessListResponse(resource="report", items=_REPORTS)


@router.post("/reports/export")
async def export_reports(
    _: User = Depends(require_permission("report", "export")),
) -> dict[str, str]:
    return {"status": "exported", "format": "csv", "rows": str(len(_REPORTS))}
