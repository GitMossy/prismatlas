import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel


class SliceQuery(BaseModel):
    zone: str | None = None
    stage: str | None = None
    planned_after: date | None = None
    planned_before: date | None = None
    owner: str | None = None
    object_type: str | None = None


class SliceResultItem(BaseModel):
    entity_id: uuid.UUID
    entity_name: str
    zone: str | None
    owner: str | None
    object_type: str | None
    planned_start: date | None
    planned_end: date | None
    current_stage: str | None
    overall_readiness: float
    ready_for_fat: bool
    ready_for_sat: bool
    blocker_count: int
    top_blocker: str | None


class SliceResponse(BaseModel):
    query: dict[str, Any]
    total: int
    results: list[SliceResultItem]
    avg_readiness: float
    fat_ready_count: int
    sat_ready_count: int
    total_blockers: int
    common_blocker_types: list[str]
