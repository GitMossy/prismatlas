import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Resource(UUIDMixin, TimestampMixin, Base):
    """
    A person or role that can be assigned to workflow task steps.
    Captures capacity for resource loading calculations.
    """
    __tablename__ = "resources"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(100))       # e.g. "Validation Engineer"
    group: Mapped[str | None] = mapped_column(String(100))      # e.g. "Automation Team"
    email: Mapped[str | None] = mapped_column(String(255))
    capacity_hours_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=8.0)
    notes: Mapped[str | None] = mapped_column(Text)

    project: Mapped["Project"] = relationship("Project")
