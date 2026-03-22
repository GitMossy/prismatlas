import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.resource import Resource


# Workflow instance lifecycle
WORKFLOW_INSTANCE_STATUSES = ("active", "completed", "suspended")

# Stage lifecycle
STAGE_STATUSES = ("pending", "active", "complete", "skipped")

# Task lifecycle
TASK_STATUSES = ("pending", "in_progress", "complete", "skipped", "blocked")


class WorkflowTemplate(UUIDMixin, TimestampMixin, Base):
    """
    A named workflow template (e.g. 'EM_Standard', 'Document_FAT').
    Templates are versioned; instances are always tied to a specific version.

    FR-4.2.3: Templates may inherit from a parent template. Parent stages are
    merged into child stages; child overrides win on key collision.
    """
    __tablename__ = "workflow_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    applies_to_type: Mapped[str] = mapped_column(String(50), nullable=False)  # object type or 'document'
    description: Mapped[str | None] = mapped_column(Text)

    # FR-4.2.3: Self-referential parent for template inheritance
    parent_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_templates.id"), nullable=True
    )

    # FR-4.2: Complexity scaling factor applied to effort estimates (1.0 = simple baseline)
    complexity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # FR-4.2: Custom attribute schema for instances of this template
    # [{"key": "tag_prefix", "type": "string", "default": null, "required": false}]
    custom_attributes: Mapped[list[Any] | None] = mapped_column(JSONB)

    versions: Mapped[list["WorkflowTemplateVersion"]] = relationship(
        "WorkflowTemplateVersion", back_populates="template", cascade="all, delete-orphan"
    )


class WorkflowTemplateVersion(UUIDMixin, Base):
    """
    An immutable versioned snapshot of a workflow template.
    The definition JSON contains all stages, tasks, and entry/exit criteria.

    Definition schema:
    {
      "stages": [
        {
          "key": "engineering",
          "name": "Engineering",
          "order": 1,
          "is_mandatory": true,
          "entry_criteria": [{"type": "stage_complete", "stage_key": "..."}],
          "exit_criteria": [{"type": "all_tasks_complete"}],
          "tasks": [
            {"key": "design_complete", "name": "Design Complete", "order": 1, "is_mandatory": true}
          ]
        }
      ]
    }
    """
    __tablename__ = "workflow_template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_templates.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # FR-4.2.4: Track which parent version this child version was derived from
    inherited_from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_template_versions.id"), nullable=True
    )

    template: Mapped["WorkflowTemplate"] = relationship("WorkflowTemplate", back_populates="versions")
    instances: Mapped[list["WorkflowInstance"]] = relationship("WorkflowInstance", back_populates="template_version")


class WorkflowInstance(UUIDMixin, TimestampMixin, Base):
    """
    A live workflow attached to a specific entity (Object or Document).
    Records the template version it was created from — template changes
    do NOT affect this instance without explicit migration.
    """
    __tablename__ = "workflow_instances"

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'object' | 'document'
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_template_versions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # FR-4.2.5: Fields overridden at instance level (not auto-propagated by parent changes).
    # Structure: {"task_key:field_name": true}
    overridden_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default='{}')

    template_version: Mapped["WorkflowTemplateVersion"] = relationship(
        "WorkflowTemplateVersion", back_populates="instances"
    )
    stage_instances: Mapped[list["StageInstance"]] = relationship(
        "StageInstance", back_populates="workflow_instance", cascade="all, delete-orphan",
        order_by="StageInstance.stage_order"
    )


class StageInstance(UUIDMixin, Base):
    """
    A live stage within a WorkflowInstance. Cannot advance to next stage
    if any entry criterion evaluates false.
    """
    __tablename__ = "stage_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_instances.id"), nullable=False
    )
    stage_key: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow_instance: Mapped["WorkflowInstance"] = relationship("WorkflowInstance", back_populates="stage_instances")
    task_instances: Mapped[list["TaskInstance"]] = relationship(
        "TaskInstance", back_populates="stage_instance", cascade="all, delete-orphan",
        order_by="TaskInstance.task_order"
    )


class TaskInstance(UUIDMixin, Base):
    """
    A live task within a StageInstance. Completion evidence is attached here.

    Scheduling fields (FR-4.3.2, FR-4.4.2):
      duration_days  — calendar duration for CPM forward/backward pass
      effort_hours   — person-hours of work (may differ from duration if parallelism > 1)
      assigned_resource_id — resource responsible for this task (optional)

    CPM dates are calculated by the schedule engine and stored here for UI use.
    """
    __tablename__ = "task_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stage_instances.id"), nullable=False
    )
    task_key: Mapped[str] = mapped_column(String(100), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    # Scheduling fields (FR-4.3.2)
    # duration_days is Float to support half-day granularity (0.5d minimum per V3 FR-4.3.2)
    duration_days: Mapped[float | None] = mapped_column(Float)
    effort_hours: Mapped[float | None] = mapped_column(Float)
    assigned_resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="SET NULL")
    )

    # CPM calculated dates (FR-4.4.2) — populated by schedule engine
    # Stored as Float day offsets to support fractional durations (0.5d granularity)
    early_start: Mapped[float | None] = mapped_column(Float)   # day offset from project start
    early_finish: Mapped[float | None] = mapped_column(Float)
    late_start: Mapped[float | None] = mapped_column(Float)
    late_finish: Mapped[float | None] = mapped_column(Float)
    total_float: Mapped[float | None] = mapped_column(Float)
    is_critical: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_near_critical: Mapped[bool] = mapped_column(default=False, nullable=False)

    stage_instance: Mapped["StageInstance"] = relationship("StageInstance", back_populates="task_instances")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="task_instance", cascade="all, delete-orphan")
    assigned_resource: Mapped["Resource | None"] = relationship("Resource")
