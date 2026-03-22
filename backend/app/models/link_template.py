"""
LinkTemplate model — FR-4.5.4

A LinkTemplate defines a pattern for automatically creating Relationships
between Objects of specified types when a new Object is added to a project.

link_type mirrors DependencyRule link types (FS|SS|FF|SF).
lag_days: positive = lag, negative = lead.
is_active: inactive templates are ignored by the applier.
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class LinkTemplate(UUIDMixin, TimestampMixin, Base):
    """
    Defines a reusable pattern: whenever an Object of source_object_type is
    created in a project, automatically link it to all Objects of
    target_object_type in the same project (subject to cycle checks).

    Columns:
      project_id          — scope to a single project
      name                — human-readable label
      source_object_type  — Object.object_type of the source
      source_stage_key    — optional stage key context (informational)
      target_object_type  — Object.object_type of the target
      target_stage_key    — optional stage key context (informational)
      link_type           — FS | SS | FF | SF
      lag_days            — scheduling lag in calendar days (default 0)
      is_active           — inactive templates are skipped by the applier
    """
    __tablename__ = "link_templates"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_object_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_stage_key: Mapped[str | None] = mapped_column(String(100))
    target_object_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_stage_key: Mapped[str | None] = mapped_column(String(100))
    link_type: Mapped[str] = mapped_column(String(2), nullable=False, default="FS")
    lag_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    project: Mapped["Project"] = relationship("Project")
