import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin


class Scenario(UUIDMixin, Base):
    """
    A what-if scenario that applies overrides to a baseline schedule — FR-4.4.6.
    Scenarios are computed in-memory; they do NOT modify live task_instances.
    """
    __tablename__ = "scenarios"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Optional: derived from a specific baseline (for EV comparison context)
    source_baseline_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("baselines.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    task_overrides: Mapped[list["ScenarioTaskOverride"]] = relationship(
        "ScenarioTaskOverride", back_populates="scenario", cascade="all, delete-orphan"
    )


class ScenarioTaskOverride(UUIDMixin, Base):
    """
    Per-task override within a scenario.
    Only the provided fields are applied; None means "use baseline value".
    """
    __tablename__ = "scenario_task_overrides"

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id"), nullable=False
    )
    task_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_instances.id"), nullable=False
    )

    # Override values — all optional
    duration_days: Mapped[int | None] = mapped_column(Integer)
    effort_hours: Mapped[float | None] = mapped_column(Float)
    start_offset_days: Mapped[int | None] = mapped_column(Integer)

    scenario: Mapped["Scenario"] = relationship("Scenario", back_populates="task_overrides")
