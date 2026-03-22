import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ── Baseline schemas ───────────────────────────────────────────────────────────

class BaselineCreate(BaseModel):
    name: str
    description: str | None = None
    # created_by is populated from auth context in the API layer (optional)
    created_by: uuid.UUID | None = None


class BaselineTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    baseline_id: uuid.UUID
    task_instance_id: uuid.UUID
    planned_start: int | None
    planned_finish: int | None
    planned_effort_hours: float | None
    planned_cost: float | None
    early_start: int | None
    early_finish: int | None
    late_start: int | None
    late_finish: int | None
    total_float: int | None


class BaselineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    created_by: uuid.UUID | None
    tasks: list[BaselineTaskResponse] = []


class EVResponse(BaseModel):
    pv: float
    ev: float
    spi: float | None
    task_count_total: int
    task_count_complete: int
