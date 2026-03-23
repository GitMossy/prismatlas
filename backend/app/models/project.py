import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.object import Object
    from app.models.document import Document


class Project(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    areas: Mapped[list["Area"]] = relationship("Area", back_populates="project", cascade="all, delete-orphan")
    objects: Mapped[list["Object"]] = relationship("Object", back_populates="project")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="project")


class Area(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "areas"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    project: Mapped["Project"] = relationship("Project", back_populates="areas")
    units: Mapped[list["Unit"]] = relationship("Unit", back_populates="area", cascade="all, delete-orphan")
    objects: Mapped[list["Object"]] = relationship("Object", back_populates="area")


class Unit(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "units"

    area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    area: Mapped["Area"] = relationship("Area", back_populates="units")
    objects: Mapped[list["Object"]] = relationship("Object", back_populates="unit")
