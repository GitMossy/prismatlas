import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

# Valid deliverable statuses — FR-4.3.6
DELIVERABLE_STATUSES = ("not_started", "in_progress", "in_review", "approved", "rejected")


class Deliverable(UUIDMixin, TimestampMixin, Base):
    """
    A formal output or work product that must be produced and approved.
    Linked to either a TaskInstance or a stage_key within a workflow.
    FR-4.3.6.
    """
    __tablename__ = "deliverables"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    # Optional link to a specific task
    task_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_instances.id"), nullable=True
    )
    # Alternative: link to a stage by key (e.g. "engineering", "fat")
    stage_key: Mapped[str | None] = mapped_column(String(100))

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_started"
    )  # one of DELIVERABLE_STATUSES

    assigned_to: Mapped[str | None] = mapped_column(String(255))
    due_date: Mapped[date | None] = mapped_column(Date)

    # Approval fields — populated when status transitions to 'approved'
    approved_by: Mapped[str | None] = mapped_column(String(255))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
