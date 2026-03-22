import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin


class Baseline(UUIDMixin, Base):
    """
    A snapshot of planned schedule values at a point in time — FR-4.4.5.
    Baselines are immutable once created; used for EV and variance analysis.
    """
    __tablename__ = "baselines"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Optional: track which user created the baseline (None = system)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    tasks: Mapped[list["BaselineTask"]] = relationship(
        "BaselineTask", back_populates="baseline", cascade="all, delete-orphan"
    )


class BaselineTask(UUIDMixin, Base):
    """
    A single task's planned schedule within a baseline.
    All date fields are integer day-offsets from the project anchor date
    (consistent with TaskInstance CPM fields).
    """
    __tablename__ = "baseline_tasks"

    baseline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("baselines.id"), nullable=False
    )
    task_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_instances.id"), nullable=False
    )

    # Planned schedule (from CPM at snapshot time)
    planned_start: Mapped[int | None] = mapped_column(Integer)
    planned_finish: Mapped[int | None] = mapped_column(Integer)
    planned_effort_hours: Mapped[float | None] = mapped_column(Float)
    planned_cost: Mapped[float | None] = mapped_column(Float)

    # CPM floats at snapshot time
    early_start: Mapped[int | None] = mapped_column(Integer)
    early_finish: Mapped[int | None] = mapped_column(Integer)
    late_start: Mapped[int | None] = mapped_column(Integer)
    late_finish: Mapped[int | None] = mapped_column(Integer)
    total_float: Mapped[int | None] = mapped_column(Integer)

    baseline: Mapped["Baseline"] = relationship("Baseline", back_populates="tasks")
