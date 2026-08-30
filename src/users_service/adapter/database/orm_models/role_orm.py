from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from users_service.adapter.database.base import Base, role_permissions, user_roles


class RoleORM(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["UserORM"]] = relationship(  # noqa: F821
        secondary=user_roles, back_populates="roles"
    )
    permissions: Mapped[list["PermissionORM"]] = relationship(  # noqa: F821
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )
