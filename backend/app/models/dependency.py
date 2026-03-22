import uuid
from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

# CPM link types (FR-4.3.4, FR-4.5.1)
LINK_TYPES = (
    "FS",   # Finish-to-Start (default): successor starts after predecessor finishes
    "SS",   # Start-to-Start: successor starts when predecessor starts
    "FF",   # Finish-to-Finish: successor finishes when predecessor finishes
    "SF",   # Start-to-Finish: successor finishes when predecessor starts
)


# Entity types that can participate in dependencies/relationships
ENTITY_TYPES = ("object", "document", "stage")

# Relationship types between entities
RELATIONSHIP_TYPES = (
    "object_to_object",       # Object depends on another Object
    "object_to_document",     # Object requires a Document
    "document_to_stage",      # Document gates a Stage
    "stage_to_stage",         # Stage depends on another Stage
    "test_to_document",       # Test result gates a Document requirement
)


class DependencyRule(UUIDMixin, TimestampMixin, Base):
    """
    A configurable rule defining a dependency between entity types.
    Rules are associated with a workflow template version (or a project for overrides).
    Deleting a rule MUST trigger re-evaluation of all affected ReadinessEvaluations.

    The condition JSON defines what state the target must be in:
    {
      "target_status": "Approved",           -- document must be in this status
      "target_stage_key": "fat_execution",   -- stage must have reached this point
      "operator": "eq" | "gte" | "in",
      "value": ...
    }
    """
    __tablename__ = "dependency_rules"

    template_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_template_versions.id")
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Source: the entity that has the dependency
    source_entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # null = applies to all of type

    # Target: what the source depends on
    target_entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # null = any of type

    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(default=True, nullable=False)

    # CPM scheduling fields (FR-4.3.4, FR-4.5.1)
    link_type: Mapped[str] = mapped_column(String(2), nullable=False, default="FS")    # FS|SS|FF|SF
    lag_days: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)        # positive = lag, negative = lead; decimal days (0.5d min)

    template_version: Mapped["WorkflowTemplateVersion | None"] = relationship("WorkflowTemplateVersion")  # type: ignore[name-defined]


class Relationship(UUIDMixin, TimestampMixin, Base):
    """
    A concrete link between two entity instances (e.g. a specific EM object
    linked to a specific FRS document). These are the instance-level counterpart
    to DependencyRules which operate at the type/template level.
    """
    __tablename__ = "relationships"

    source_entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    target_entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
