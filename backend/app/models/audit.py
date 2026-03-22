import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class AuditLog(UUIDMixin, Base):
    """
    Immutable audit trail entry. No updated_at — these rows are never modified.
    NFR-7.3: GMP-compliant audit log with actor, entity, action, and before/after values.
    """
    __tablename__ = "audit_logs"

    # Context
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # What was changed
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)

    # Field-level granularity (optional — None means whole-record action)
    field_name: Mapped[str | None] = mapped_column(String(100))
    old_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)

    # Single immutable timestamp (not TimestampMixin which adds updated_at)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
