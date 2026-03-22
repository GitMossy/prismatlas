import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class ReadinessEvaluation(UUIDMixin, Base):
    """
    A point-in-time snapshot of an entity's readiness across all three dimensions.
    Always derived — never manually set.
    Re-evaluated on any state change (task completion, document status change,
    dependency rule add/delete, relationship change).

    blockers JSON structure:
    [
      {
        "type": "document" | "dependency" | "task" | "stage_gate",
        "entity_id": "uuid",
        "entity_name": "string",
        "reason": "human-readable explanation",
        "severity": "blocking" | "warning"
      }
    ]
    """
    __tablename__ = "readiness_evaluations"

    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'object' | 'document'
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Three-dimensional readiness (0.0 – 1.0)
    technical_readiness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    document_readiness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stage_readiness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_readiness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Milestone gates
    ready_for_fat: Mapped[bool] = mapped_column(default=False, nullable=False)
    ready_for_sat: Mapped[bool] = mapped_column(default=False, nullable=False)

    blockers: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    next_action: Mapped[str | None] = mapped_column(String(500))

    # E2: Marks the single most-recent evaluation for this entity.
    # Set to True on the new row; bulk-set to False on all previous rows for
    # the same entity_id. Allows efficient current-readiness queries without
    # a subquery.  Index: ix_readiness_entity_current(entity_id, is_current).
    is_current: Mapped[bool] = mapped_column(default=False, nullable=False)

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
