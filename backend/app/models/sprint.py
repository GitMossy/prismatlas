import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Release(UUIDMixin, TimestampMixin, Base):
    """
    A product release grouping multiple sprints — FR-4.7.
    """
    __tablename__ = "releases"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_date: Mapped[date | None] = mapped_column(Date)

    sprints: Mapped[list["Sprint"]] = relationship("Sprint", back_populates="release")


class Sprint(UUIDMixin, TimestampMixin, Base):
    """
    A time-boxed sprint within a release — FR-4.7.
    May exist without a release (standalone sprint).
    """
    __tablename__ = "sprints"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("releases.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    capacity_hours: Mapped[float | None] = mapped_column(Float)

    release: Mapped["Release | None"] = relationship("Release", back_populates="sprints")
    task_assignments: Mapped[list["TaskSprintAssignment"]] = relationship(
        "TaskSprintAssignment", back_populates="sprint", cascade="all, delete-orphan"
    )


class TaskSprintAssignment(UUIDMixin, Base):
    """
    Assignment of a TaskInstance to a Sprint with an optional hours estimate.
    """
    __tablename__ = "task_sprint_assignments"

    task_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_instances.id"), nullable=False
    )
    sprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sprints.id"), nullable=False
    )
    assigned_hours: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sprint: Mapped["Sprint"] = relationship("Sprint", back_populates="task_assignments")
