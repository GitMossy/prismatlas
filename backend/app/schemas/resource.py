import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResourceCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    role: str | None = None
    group: str | None = None
    email: str | None = None
    capacity_hours_per_day: float = 8.0
    notes: str | None = None


class ResourceUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    group: str | None = None
    email: str | None = None
    capacity_hours_per_day: float | None = None
    notes: str | None = None


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    role: str | None
    group: str | None
    email: str | None
    capacity_hours_per_day: float
    notes: str | None
    created_at: datetime
    updated_at: datetime
