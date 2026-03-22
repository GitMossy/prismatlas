import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.deliverable import DELIVERABLE_STATUSES


class DeliverableCreate(BaseModel):
    project_id: uuid.UUID
    task_instance_id: uuid.UUID | None = None
    stage_key: str | None = None
    name: str
    description: str | None = None
    status: str = "not_started"
    assigned_to: str | None = None
    due_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in DELIVERABLE_STATUSES:
            raise ValueError(f"status must be one of {DELIVERABLE_STATUSES}")
        return v


class DeliverableUpdate(BaseModel):
    task_instance_id: uuid.UUID | None = None
    stage_key: str | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    due_date: date | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in DELIVERABLE_STATUSES:
            raise ValueError(f"status must be one of {DELIVERABLE_STATUSES}")
        return v


class DeliverableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    task_instance_id: uuid.UUID | None
    stage_key: str | None
    name: str
    description: str | None
    status: str
    assigned_to: str | None
    due_date: date | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
