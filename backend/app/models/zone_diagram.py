"""
ZoneDiagram and ZoneDiagramPin models — FR-4.6.3

ZoneDiagram: image overlay for an area showing object positions.
ZoneDiagramPin: a pin placed at (x_pct, y_pct) on the diagram image, linked to an object.
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Area
    from app.models.object import Object


class ZoneDiagram(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "zone_diagrams"

    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("areas.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # image_url is a Supabase Storage URL — storage handled client-side
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    image_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1920)
    image_height: Mapped[int] = mapped_column(Integer, nullable=False, default=1080)

    area: Mapped["Area"] = relationship("Area")
    pins: Mapped[list["ZoneDiagramPin"]] = relationship(
        "ZoneDiagramPin", back_populates="diagram", cascade="all, delete-orphan"
    )


class ZoneDiagramPin(UUIDMixin, Base):
    __tablename__ = "zone_diagram_pins"

    zone_diagram_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zone_diagrams.id", ondelete="CASCADE"), nullable=False
    )
    object_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("objects.id", ondelete="CASCADE"), nullable=False
    )
    # x_pct and y_pct are 0.0–1.0 fractions of image width/height
    x_pct: Mapped[float] = mapped_column(Float, nullable=False)
    y_pct: Mapped[float] = mapped_column(Float, nullable=False)

    diagram: Mapped["ZoneDiagram"] = relationship("ZoneDiagram", back_populates="pins")
    object: Mapped["Object"] = relationship("Object")
