import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DependencyRuleCreate(BaseModel):
    template_version_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    source_entity_type: str
    source_entity_id: uuid.UUID | None = None  # None = applies to all of type
    target_entity_type: str
    target_entity_id: uuid.UUID | None = None  # None = any of type
    condition: dict[str, Any]
    is_mandatory: bool = True
    # CPM scheduling fields (FR-4.3.4, FR-4.5.1)
    link_type: str = "FS"    # FS | SS | FF | SF
    lag_days: float = 0.0    # decimal days; positive = lag, negative = lead


class DependencyRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template_version_id: uuid.UUID | None
    project_id: uuid.UUID | None
    name: str
    description: str | None
    source_entity_type: str
    source_entity_id: uuid.UUID | None
    target_entity_type: str
    target_entity_id: uuid.UUID | None
    condition: dict[str, Any]
    is_mandatory: bool
    link_type: str
    lag_days: float
    created_at: datetime
    updated_at: datetime


class RelationshipCreate(BaseModel):
    source_entity_type: str
    source_entity_id: uuid.UUID
    target_entity_type: str
    target_entity_id: uuid.UUID
    relationship_type: str
    is_mandatory: bool = True
    notes: str | None = None


class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_entity_type: str
    source_entity_id: uuid.UUID
    target_entity_type: str
    target_entity_id: uuid.UUID
    relationship_type: str
    is_mandatory: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
