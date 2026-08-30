from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from users_service.adapter.database.base import Base, role_permissions


class PermissionORM(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permission_resource_action"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    resource: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list["RoleORM"]] = relationship(  # noqa: F821
        secondary=role_permissions, back_populates="permissions"
    )
