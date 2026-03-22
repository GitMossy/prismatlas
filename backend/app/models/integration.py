"""
IntegrationConfig model — stores third-party integration settings per project.

Supported providers: jira, azdo (Azure DevOps).

Security note: raw API tokens must NEVER be stored in plaintext. The config
JSONB field should hold an encrypted blob; the encryption key is held in the
application environment (INTEGRATION_SECRET_KEY env var), never in the DB.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


VALID_PROVIDERS = ("jira", "azdo")
VALID_SYNC_DIRECTIONS = ("push", "pull", "bidirectional")


class IntegrationConfig(UUIDMixin, TimestampMixin, Base):
    """
    Stores connection parameters and field mappings for one integration
    (e.g. Jira or Azure DevOps) attached to a project.

    config JSONB example (values encrypted at rest):
      {
        "base_url": "https://mycompany.atlassian.net",
        "project_key": "PA",
        "token_enc": "<encrypted-base64>"   // never a raw token
      }

    field_mapping JSONB example:
      {
        "task_name": "summary",
        "status": "status.name",
        "completed_at": "resolutiondate"
      }
    """
    __tablename__ = "integration_configs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # 'jira' | 'azdo'

    # Connection parameters — tokens stored encrypted (see security note above)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # How PrismAtlas fields map to provider fields
    field_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    sync_direction: Mapped[str] = mapped_column(
        String(20), nullable=False, default="push"
    )  # 'push' | 'pull' | 'bidirectional'

    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
