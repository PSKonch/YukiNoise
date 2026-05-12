from uuid import uuid4
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, UUID, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yn.shared.database import Base


if TYPE_CHECKING:
    from yn.modules.profiles.model import Profile


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # relationships
    profile: Mapped["Profile"] = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
