import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# ── Release schemas ────────────────────────────────────────────────────────────

class ReleaseCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    description: str | None = None
    target_date: date | None = None


class ReleaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_date: date | None = None


class ReleaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    target_date: date | None
    created_at: datetime
    updated_at: datetime


# ── Sprint schemas ─────────────────────────────────────────────────────────────

class SprintCreate(BaseModel):
    project_id: uuid.UUID
    release_id: uuid.UUID | None = None
    name: str
    start_date: date | None = None
    end_date: date | None = None
    capacity_hours: float | None = None


class SprintUpdate(BaseModel):
    release_id: uuid.UUID | None = None
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    capacity_hours: float | None = None


class SprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    release_id: uuid.UUID | None
    name: str
    start_date: date | None
    end_date: date | None
    capacity_hours: float | None
    created_at: datetime
    updated_at: datetime


# ── Task assignment schemas ────────────────────────────────────────────────────

class TaskAssignRequest(BaseModel):
    task_instance_id: uuid.UUID
    assigned_hours: float | None = None


class TaskAssignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_instance_id: uuid.UUID
    sprint_id: uuid.UUID
    assigned_hours: float | None
    created_at: datetime


# ── Burndown data point ────────────────────────────────────────────────────────

class BurndownPoint(BaseModel):
    date: date
    planned_remaining: float
    actual_remaining: float
