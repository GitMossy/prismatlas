import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_instance_id: uuid.UUID
    file_name: str
    file_url: str
    description: str | None
    uploaded_by: str
    uploaded_at: datetime
