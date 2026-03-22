import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClassDefinitionCreate(BaseModel):
    project_id: uuid.UUID
    area_id: uuid.UUID | None = None
    workflow_template_id: uuid.UUID | None = None
    name: str
    object_type: str
    description: str | None = None
    instance_count: int = Field(default=1, ge=1)
    complexity: float = Field(default=1.0, ge=0.1)
    custom_attributes: list[Any] | None = None


class ClassDefinitionUpdate(BaseModel):
    name: str | None = None
    area_id: uuid.UUID | None = None
    workflow_template_id: uuid.UUID | None = None
    description: str | None = None
    instance_count: int | None = Field(default=None, ge=1)
    complexity: float | None = Field(default=None, ge=0.1)
    custom_attributes: list[Any] | None = None


class ClassDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    area_id: uuid.UUID | None
    workflow_template_id: uuid.UUID | None
    name: str
    object_type: str
    description: str | None
    instance_count: int
    complexity: float
    custom_attributes: list[Any] | None
    created_at: datetime
    updated_at: datetime
