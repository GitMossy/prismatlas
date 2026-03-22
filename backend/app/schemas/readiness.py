import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class BlockerSchema(BaseModel):
    type: str  # "document" | "dependency" | "task" | "stage_gate"
    entity_id: str
    entity_name: str
    reason: str
    severity: str  # "blocking" | "warning"


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    technical_readiness: float
    document_readiness: float
    stage_readiness: float
    overall_readiness: float
    ready_for_fat: bool
    ready_for_sat: bool
    blockers: list[dict[str, Any]]
    next_action: str | None
    evaluated_at: datetime


class ProjectReadinessSummaryItem(BaseModel):
    entity_id: uuid.UUID
    entity_name: str
    entity_type: str
    object_type: str | None = None
    overall_readiness: float
    ready_for_fat: bool
    ready_for_sat: bool
    blocker_count: int


class AreaReadinessSummary(BaseModel):
    area_id: uuid.UUID
    area_name: str
    object_count: int
    avg_readiness: float
    fat_ready_count: int
    sat_ready_count: int
    blocker_count: int
