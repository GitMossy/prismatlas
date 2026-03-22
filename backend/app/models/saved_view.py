"""
SavedView model — saved_views table

Stores user-defined matrix/pivot configurations for reuse.
FR-4.6.1, FR-4.6.2
"""
import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class SavedView(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "saved_views"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    # user_id is nullable — views can be project-wide or user-specific
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # config stores the matrix type and axis/metric configuration
    # e.g. {"view": "custom", "rows": "area", "cols": "object_type", "metric": "readiness"}
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    project: Mapped["Project"] = relationship("Project")
