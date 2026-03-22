"""
Webhook management API — create, list, delete webhook subscriptions and view
delivery history.
"""
import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.webhook import WebhookSubscription, WebhookDelivery

router = APIRouter(prefix="/projects", tags=["webhooks"])


@router.post("/{project_id}/webhooks")
def create_webhook(
    project_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
):
    """Register a new webhook subscription.

    Required body fields: name, url, secret, events (list of event types).
    Supported event types: task.completed, stage.advanced, document.status_changed, *
    The raw secret is hashed (SHA-256) before storage and never returned.
    """
    name = body.get("name", "")
    url = body.get("url", "")
    secret = body.pop("secret", "") or ""
    events = body.get("events", ["*"])

    if not name:
        raise HTTPException(400, "name is required")
    if not url:
        raise HTTPException(400, "url is required")
    if not secret:
        raise HTTPException(400, "secret is required (used for HMAC signing)")

    secret_hash = hashlib.sha256(secret.encode()).hexdigest()

    sub = WebhookSubscription(
        project_id=project_id,
        name=name,
        url=url,
        secret_hash=secret_hash,
        events=events,
        is_active=body.get("is_active", True),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return _safe_sub(sub)


@router.get("/{project_id}/webhooks")
def list_webhooks(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """List all webhook subscriptions for this project."""
    subs = (
        db.query(WebhookSubscription)
        .filter(WebhookSubscription.project_id == project_id)
        .all()
    )
    return [_safe_sub(s) for s in subs]


@router.get("/{project_id}/webhooks/{webhook_id}")
def get_webhook(
    project_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get a single webhook subscription."""
    sub = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == webhook_id,
        WebhookSubscription.project_id == project_id,
    ).first()
    if not sub:
        raise HTTPException(404, "Webhook subscription not found")
    return _safe_sub(sub)


@router.patch("/{project_id}/webhooks/{webhook_id}")
def update_webhook(
    project_id: uuid.UUID,
    webhook_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
):
    """Update a webhook subscription (name, url, events, is_active)."""
    sub = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == webhook_id,
        WebhookSubscription.project_id == project_id,
    ).first()
    if not sub:
        raise HTTPException(404, "Webhook subscription not found")

    for field in ("name", "url", "events", "is_active"):
        if field in body:
            setattr(sub, field, body[field])

    db.commit()
    db.refresh(sub)
    return _safe_sub(sub)


@router.delete("/{project_id}/webhooks/{webhook_id}", status_code=204)
def delete_webhook(
    project_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Delete a webhook subscription and all its delivery records."""
    sub = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == webhook_id,
        WebhookSubscription.project_id == project_id,
    ).first()
    if sub:
        db.delete(sub)
        db.commit()


@router.get("/{project_id}/webhooks/{webhook_id}/deliveries")
def list_deliveries(
    project_id: uuid.UUID,
    webhook_id: uuid.UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List recent delivery attempts for a webhook subscription."""
    # Verify the subscription belongs to this project
    sub = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == webhook_id,
        WebhookSubscription.project_id == project_id,
    ).first()
    if not sub:
        raise HTTPException(404, "Webhook subscription not found")

    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.subscription_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        {
            "id": str(d.id),
            "event": d.event,
            "status": d.status,
            "attempt_count": d.attempt_count,
            "last_attempted_at": d.last_attempted_at.isoformat() if d.last_attempted_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in deliveries
    ]


def _safe_sub(sub: WebhookSubscription) -> dict:
    """Return webhook subscription without secret_hash."""
    return {
        "id": str(sub.id),
        "project_id": str(sub.project_id),
        "name": sub.name,
        "url": sub.url,
        "events": sub.events,
        "is_active": sub.is_active,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    }
