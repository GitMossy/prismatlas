"""
Zone Diagram API — FR-4.6.3

Endpoints:
  POST /areas/{area_id}/zone-diagrams      — create diagram
  GET  /areas/{area_id}/zone-diagrams      — list diagrams for area
  GET  /zone-diagrams/{id}                 — get diagram with pins
  POST /zone-diagrams/{id}/pins            — add pin
  PUT  /zone-diagrams/{id}/pins/{pin_id}   — update pin position
  DELETE /zone-diagrams/{id}/pins/{pin_id} — remove pin
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Area
from app.models.object import Object
from app.models.zone_diagram import ZoneDiagram, ZoneDiagramPin

areas_router = APIRouter(prefix="/areas", tags=["zone-diagrams"])
diagrams_router = APIRouter(prefix="/zone-diagrams", tags=["zone-diagrams"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ZoneDiagramCreate(BaseModel):
    name: str
    image_url: str
    image_width: int = 1920
    image_height: int = 1080


class ZoneDiagramPinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    zone_diagram_id: uuid.UUID
    object_id: uuid.UUID
    x_pct: float
    y_pct: float


class ZoneDiagramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    area_id: uuid.UUID
    name: str
    image_url: str
    image_width: int
    image_height: int
    pins: list[ZoneDiagramPinOut]


class ZoneDiagramSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    area_id: uuid.UUID
    name: str
    image_url: str
    image_width: int
    image_height: int


class PinCreate(BaseModel):
    object_id: uuid.UUID
    x_pct: float
    y_pct: float

    @field_validator("x_pct", "y_pct")
    @classmethod
    def between_zero_and_one(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Coordinate must be between 0.0 and 1.0")
        return v


class PinUpdate(BaseModel):
    x_pct: float
    y_pct: float

    @field_validator("x_pct", "y_pct")
    @classmethod
    def between_zero_and_one(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Coordinate must be between 0.0 and 1.0")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@areas_router.post("/{area_id}/zone-diagrams", response_model=ZoneDiagramSummary, status_code=201)
def create_zone_diagram(
    area_id: uuid.UUID,
    body: ZoneDiagramCreate,
    db: Session = Depends(get_db),
):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    diagram = ZoneDiagram(area_id=area_id, **body.model_dump())
    db.add(diagram)
    db.commit()
    db.refresh(diagram)
    return diagram


@areas_router.get("/{area_id}/zone-diagrams", response_model=list[ZoneDiagramSummary])
def list_zone_diagrams(area_id: uuid.UUID, db: Session = Depends(get_db)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return db.query(ZoneDiagram).filter(ZoneDiagram.area_id == area_id).all()


@diagrams_router.get("/{diagram_id}", response_model=ZoneDiagramOut)
def get_zone_diagram(diagram_id: uuid.UUID, db: Session = Depends(get_db)):
    diagram = db.query(ZoneDiagram).filter(ZoneDiagram.id == diagram_id).first()
    if not diagram:
        raise HTTPException(status_code=404, detail="Zone diagram not found")
    return diagram


@diagrams_router.post("/{diagram_id}/pins", response_model=ZoneDiagramPinOut, status_code=201)
def add_pin(
    diagram_id: uuid.UUID,
    body: PinCreate,
    db: Session = Depends(get_db),
):
    diagram = db.query(ZoneDiagram).filter(ZoneDiagram.id == diagram_id).first()
    if not diagram:
        raise HTTPException(status_code=404, detail="Zone diagram not found")
    obj = db.query(Object).filter(Object.id == body.object_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    pin = ZoneDiagramPin(zone_diagram_id=diagram_id, **body.model_dump())
    db.add(pin)
    db.commit()
    db.refresh(pin)
    return pin


@diagrams_router.put("/{diagram_id}/pins/{pin_id}", response_model=ZoneDiagramPinOut)
def update_pin(
    diagram_id: uuid.UUID,
    pin_id: uuid.UUID,
    body: PinUpdate,
    db: Session = Depends(get_db),
):
    pin = (
        db.query(ZoneDiagramPin)
        .filter(ZoneDiagramPin.id == pin_id, ZoneDiagramPin.zone_diagram_id == diagram_id)
        .first()
    )
    if not pin:
        raise HTTPException(status_code=404, detail="Pin not found")
    pin.x_pct = body.x_pct
    pin.y_pct = body.y_pct
    db.commit()
    db.refresh(pin)
    return pin


@diagrams_router.delete("/{diagram_id}/pins/{pin_id}", status_code=204)
def delete_pin(
    diagram_id: uuid.UUID,
    pin_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    pin = (
        db.query(ZoneDiagramPin)
        .filter(ZoneDiagramPin.id == pin_id, ZoneDiagramPin.zone_diagram_id == diagram_id)
        .first()
    )
    if not pin:
        raise HTTPException(status_code=404, detail="Pin not found")
    db.delete(pin)
    db.commit()
