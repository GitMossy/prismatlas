"""
EffortMatrixCell — FR-4.3.3 Effort Estimation Matrix

Stores base effort estimates per (WorkflowTemplate, step_key) pair.
The actual effort for a task = base_effort_hours × complexity_multiplier × effort_scaling.

Grid interpretation:
  rows    = WorkflowTemplate (Type axis)
  columns = step_key within that template (Activity axis)
  cell    = base_effort_hours for that (Type, Step) combination

Complexity multiplier is applied from ClassDefinition.complexity.
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.workflow import WorkflowTemplate


class EffortMatrixCell(UUIDMixin, TimestampMixin, Base):
    """
    One cell in the Effort Estimation Matrix.

    workflow_template_id + step_key = unique cell address.
    base_effort_hours is the estimate before any complexity/scaling multipliers.
    notes can explain assumptions (e.g. "assumes 1 engineer, no re-work").
    """
    __tablename__ = "effort_matrix_cells"
    __table_args__ = (
        UniqueConstraint("workflow_template_id", "step_key", name="uq_effort_matrix_cell"),
    )

    workflow_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_key: Mapped[str] = mapped_column(String(100), nullable=False)
    step_name: Mapped[str | None] = mapped_column(String(255))  # denormalised for display
    base_effort_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text)

    workflow_template: Mapped["WorkflowTemplate"] = relationship("WorkflowTemplate")
