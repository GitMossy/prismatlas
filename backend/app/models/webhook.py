"""
Webhook models — subscription + delivery tracking.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class WebhookSubscription(UUIDMixin, TimestampMixin, Base):
    """
    A registered webhook endpoint for a project.
    When a matching event fires, a WebhookDelivery row is created and the
    HTTP call is dispatched as a FastAPI BackgroundTask.

    secret_hash: SHA-256 of the caller-supplied secret. The raw secret is
    never stored. HMAC-SHA256 signatures use the secret retrieved from the
    caller at registration time (store it securely on the caller's side).
    """
    __tablename__ = "webhook_subscriptions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    # SHA-256 hash of the secret (raw secret is never persisted)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # PostgreSQL ARRAY of event type strings, e.g. ["task.completed", "*"]
    events: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        "WebhookDelivery", back_populates="subscription", cascade="all, delete-orphan"
    )


class WebhookDelivery(UUIDMixin, Base):
    """
    A single webhook delivery attempt record.
    Created synchronously when an event fires; HTTP dispatch runs async.
    """
    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # 'pending' | 'delivered' | 'failed'

    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    subscription: Mapped["WebhookSubscription"] = relationship(
        "WebhookSubscription", back_populates="deliveries"
    )
