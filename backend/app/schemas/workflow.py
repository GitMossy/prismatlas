import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# --- Workflow Templates ---

class WorkflowTemplateCreate(BaseModel):
    name: str
    applies_to_type: str  # object type (e.g. "EM") or "document"
    description: str | None = None
    complexity: float = 1.0
    custom_attributes: list[Any] | None = None


class WorkflowTemplateUpdate(BaseModel):
    name: str | None = None
    applies_to_type: str | None = None
    description: str | None = None
    complexity: float | None = None
    custom_attributes: list[Any] | None = None


class WorkflowTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    applies_to_type: str
    description: str | None
    complexity: float
    custom_attributes: list[Any] | None
    created_at: datetime
    updated_at: datetime


class WorkflowTemplateVersionCreate(BaseModel):
    definition: dict[str, Any]


class WorkflowTemplateVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template_id: uuid.UUID
    version_number: int
    definition: dict[str, Any]
    is_active: bool
    created_at: datetime


# --- Workflow Instances ---

class WorkflowInstantiateRequest(BaseModel):
    template_version_id: uuid.UUID


class TaskInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage_instance_id: uuid.UUID
    task_key: str
    task_name: str
    task_order: int
    is_mandatory: bool
    status: str
    completed_at: datetime | None
    completed_by: str | None
    notes: str | None
    # Scheduling fields (FR-4.3.2 — decimal days, 0.5d minimum)
    duration_days: float | None
    effort_hours: float | None
    assigned_resource_id: uuid.UUID | None
    # CPM dates (float day offsets — fractional duration support)
    early_start: float | None
    early_finish: float | None
    late_start: float | None
    late_finish: float | None
    total_float: float | None
    is_critical: bool


class StageInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_instance_id: uuid.UUID
    stage_key: str
    stage_name: str
    stage_order: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    task_instances: list[TaskInstanceResponse]


class WorkflowInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    template_version_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    stage_instances: list[StageInstanceResponse]


# --- Stage / Task updates ---

class TaskCompleteRequest(BaseModel):
    completed_by: str
    notes: str | None = None


class StageAdvanceResponse(BaseModel):
    message: str
    completed_stage: str
    next_stage: str | None
    workflow_status: str
