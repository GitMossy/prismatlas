"""
HierarchyNode, EntityHierarchyMembership, HierarchyVersion — FR-4.1

Supports unlimited-depth hierarchies across eight dimensions:
  ZBS — Zone Breakdown Structure
  EBS — Equipment Breakdown Structure (alias: ZBS in prior versions)
  OBS — Organisation Breakdown Structure
  TBS — Tag Breakdown Structure
  VBS — Vendor Breakdown Structure
  RBS — Resource Breakdown Structure
  CBS — Configuration Breakdown Structure (V3: software/configuration items)
  ABS — Activity Breakdown Structure    (V3: activities/work packages)
  SBS — System Breakdown Structure      (V3: systems and sub-systems)
"""
import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.workflow import WorkflowTemplate

HIERARCHY_DIMENSIONS = ("ZBS", "EBS", "OBS", "TBS", "VBS", "RBS", "CBS", "ABS", "SBS")


class HierarchyNode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "hierarchy_nodes"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(10), nullable=False)  # ZBS|EBS|OBS|TBS|VBS|RBS|CBS|ABS|SBS
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    workflow_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Cross-node dependency: objects here depend on objects in this other node
    depends_on_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hierarchy_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Condition that objects in depends_on_node must satisfy, e.g.
    # {"target_status": "complete"} or {"target_stage_key": "engineering", "operator": "complete"}
    dependency_condition: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hierarchy_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    project: Mapped["Project"] = relationship("Project")
    workflow_template: Mapped["WorkflowTemplate | None"] = relationship("WorkflowTemplate", foreign_keys=[workflow_template_id])
    parent: Mapped["HierarchyNode | None"] = relationship(
        "HierarchyNode",
        back_populates="children",
        remote_side="HierarchyNode.id",
        foreign_keys="[HierarchyNode.parent_id]",
    )
    children: Mapped[list["HierarchyNode"]] = relationship(
        "HierarchyNode",
        back_populates="parent",
        foreign_keys="[HierarchyNode.parent_id]",
        order_by="HierarchyNode.position",
    )
    memberships: Mapped[list["EntityHierarchyMembership"]] = relationship(
        "EntityHierarchyMembership", back_populates="node", cascade="all, delete-orphan"
    )


class EntityHierarchyMembership(Base):
    """
    Maps an entity (object or document) to a hierarchy node.
    entity_type: 'object' | 'document'
    entity_id: UUID of the object or document
    """
    __tablename__ = "entity_hierarchy_memberships"
    __table_args__ = (
        UniqueConstraint("entity_id", "node_id", name="uq_entity_node"),
    )

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, primary_key=True)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hierarchy_nodes.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    node: Mapped["HierarchyNode"] = relationship("HierarchyNode", back_populates="memberships")


class HierarchyVersion(UUIDMixin, Base):
    """
    Snapshot of a hierarchy dimension at a point in time.
    Used for diff comparison (FR-4.1 hierarchy versioning).
    """
    __tablename__ = "hierarchy_versions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(10), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship("Project")
