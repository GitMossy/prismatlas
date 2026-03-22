import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    document_type: str  # FRS, SDD, FAT_Protocol, FAT_Report, SAT_Protocol, etc.
    status: str = "Draft"
    description: str | None = None
    external_ref: str | None = None


class DocumentUpdate(BaseModel):
    name: str | None = None
    document_type: str | None = None
    status: str | None = None
    description: str | None = None
    external_ref: str | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    document_type: str
    status: str
    description: str | None
    external_ref: str | None
    created_at: datetime
    updated_at: datetime
