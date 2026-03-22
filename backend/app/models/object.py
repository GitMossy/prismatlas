import uuid
from typing import TYPE_CHECKING

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project, Area, Unit
    from app.models.workflow import WorkflowInstance
    from app.models.readiness import ReadinessEvaluation
    from app.models.class_definition import ClassDefinition


# OBJECT_TYPES is intentionally not a closed enum (V3 CONFLICT-1 resolution).
# Valid values are defined by the project's ClassDefinition/Type library.
# The legacy DeltaV types (IO, CM, EM, Phase, Recipe, Unit_Procedure, Batch, Other)
# remain valid but are no longer the only permissible values.

# Valid statuses for an object
OBJECT_STATUSES = ("not_started", "in_progress", "blocked", "complete")


class Object(UUIDMixin, TimestampMixin, Base):
    """
    A schedule object (any type — EM, Phase, IO, CM, PLC, HMI, etc.).
    object_type is a free-text field; its valid values are defined by the
    project's Type/ClassDefinition library (V3 CONFLICT-1 resolution).
    Objects are the primary entities that progress through workflows.
    """
    __tablename__ = "objects"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    area_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("areas.id"))
    unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"))
    parent_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("objects.id", ondelete="SET NULL"), nullable=True
    )
    class_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_definitions.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_type: Mapped[str] = mapped_column(String(50), nullable=False)  # EM, IO, CM, Phase, etc.
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="not_started")
    description: Mapped[str | None] = mapped_column(Text)
    zone: Mapped[str | None] = mapped_column(String(100))
    planned_start: Mapped[date | None] = mapped_column(Date)
    planned_end: Mapped[date | None] = mapped_column(Date)
    owner: Mapped[str | None] = mapped_column(String(255))

    project: Mapped["Project"] = relationship("Project", back_populates="objects")
    area: Mapped["Area | None"] = relationship("Area", back_populates="objects")
    unit: Mapped["Unit | None"] = relationship("Unit", back_populates="objects")
    parent_object: Mapped["Object | None"] = relationship(
        "Object", back_populates="child_objects",
        remote_side="Object.id", foreign_keys="[Object.parent_object_id]"
    )
    child_objects: Mapped[list["Object"]] = relationship(
        "Object", back_populates="parent_object", foreign_keys="[Object.parent_object_id]"
    )

    class_definition: Mapped["ClassDefinition | None"] = relationship("ClassDefinition")

    workflow_instances: Mapped[list["WorkflowInstance"]] = relationship(
        "WorkflowInstance",
        primaryjoin="and_(WorkflowInstance.entity_type=='object', foreign(WorkflowInstance.entity_id)==Object.id)",
        viewonly=True,
    )
    readiness_evaluations: Mapped[list["ReadinessEvaluation"]] = relationship(
        "ReadinessEvaluation",
        primaryjoin="and_(ReadinessEvaluation.entity_type=='object', foreign(ReadinessEvaluation.entity_id)==Object.id)",
        viewonly=True,
    )
