import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project, Area
    from app.models.workflow import WorkflowTemplate


class ClassDefinition(UUIDMixin, TimestampMixin, Base):
    """
    Represents a class (template-level concept) for a group of similar objects.

    In the DART/3D-WBS model this is the 'Class' in PBS (What axis):
      Class → Instance Set (a collection of objects of this class in an Area)

    instance_count × complexity × base_effort_hours = estimated total effort.
    Workflow instantiation can auto-generate instance_count WorkflowInstances
    when this class is applied to a specific area.
    """
    __tablename__ = "class_definitions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    area_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("areas.id")
    )
    workflow_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_templates.id")
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_type: Mapped[str] = mapped_column(String(50), nullable=False)  # EM, IO, CM, etc.
    description: Mapped[str | None] = mapped_column(Text)

    # Instance Set cardinality
    instance_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Complexity scaling (1.0 = simple, 2.0 = complex, 3.0 = very complex)
    complexity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Effort scaling mode: linear | sqrt | fixed (FR-4.4.3, BR-5.5)
    effort_scaling_mode: Mapped[str] = mapped_column(String(10), nullable=False, server_default="linear")

    # Custom attributes schema: [{"key": "tag_prefix", "type": "string", "default": "FIC"}]
    custom_attributes: Mapped[list[Any] | None] = mapped_column(JSONB)

    project: Mapped["Project"] = relationship("Project")
    area: Mapped["Area | None"] = relationship("Area")
    workflow_template: Mapped["WorkflowTemplate | None"] = relationship("WorkflowTemplate")
