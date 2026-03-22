import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.workflow import WorkflowInstance
    from app.models.readiness import ReadinessEvaluation


# Valid document types in DeltaV projects
DOCUMENT_TYPES = ("FRS", "SDD", "FAT_Protocol", "FAT_Report", "SAT_Protocol", "SAT_Report", "IQ", "OQ", "PQ", "Other")

# Valid document statuses (document lifecycle)
DOCUMENT_STATUSES = ("Draft", "In_Review", "Approved", "Superseded", "Obsolete")


class Document(UUIDMixin, TimestampMixin, Base):
    """
    A project document (FRS, SDD, FAT/SAT protocol, etc.).
    Documents are active workflow entities — they have their own workflows
    and can be blockers for object readiness.
    """
    __tablename__ = "documents"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # FRS, SDD, FAT_Protocol, etc.
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Draft")
    description: Mapped[str | None] = mapped_column(Text)
    external_ref: Mapped[str | None] = mapped_column(String(255))  # e.g. doc number in external DMS

    project: Mapped["Project"] = relationship("Project", back_populates="documents")

    workflow_instances: Mapped[list["WorkflowInstance"]] = relationship(
        "WorkflowInstance",
        primaryjoin="and_(WorkflowInstance.entity_type=='document', foreign(WorkflowInstance.entity_id)==Document.id)",
        viewonly=True,
    )
    readiness_evaluations: Mapped[list["ReadinessEvaluation"]] = relationship(
        "ReadinessEvaluation",
        primaryjoin="and_(ReadinessEvaluation.entity_type=='document', foreign(ReadinessEvaluation.entity_id)==Document.id)",
        viewonly=True,
    )
