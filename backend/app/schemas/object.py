import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ObjectCreate(BaseModel):
    project_id: uuid.UUID
    area_id: uuid.UUID | None = None
    unit_id: uuid.UUID | None = None
    parent_object_id: uuid.UUID | None = None
    name: str
    object_type: str  # EM, IO, CM, Phase, Recipe, etc.
    status: str = "active"
    description: str | None = None
    zone: str | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    owner: str | None = None


class ObjectUpdate(BaseModel):
    area_id: uuid.UUID | None = None
    unit_id: uuid.UUID | None = None
    parent_object_id: uuid.UUID | None = None
    name: str | None = None
    object_type: str | None = None
    status: str | None = None
    description: str | None = None
    zone: str | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    owner: str | None = None


class ObjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    area_id: uuid.UUID | None
    unit_id: uuid.UUID | None
    parent_object_id: uuid.UUID | None
    name: str
    object_type: str
    status: str
    description: str | None
    zone: str | None
    planned_start: date | None
    planned_end: date | None
    owner: str | None
    created_at: datetime
    updated_at: datetime
