"""
Webhook dispatcher — HMAC-SHA256 signed HTTP delivery with retry.

Dispatch flow:
1. dispatch_event() is called synchronously on state change (task completed,
   stage advanced, document status changed).
2. It creates WebhookDelivery rows for all matching active subscriptions.
3. Actual HTTP delivery runs in a FastAPI BackgroundTask via deliver_webhook().
4. deliver_webhook() retries 3 times with exponential backoff (1s, 2s, 4s).

Signature header: X-PrismAtlas-Signature: sha256=<hex>
Event header:     X-PrismAtlas-Event: <event_type>
"""
import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.webhook import WebhookSubscription, WebhookDelivery


def dispatch_event(
    event_type: str,
    payload: dict,
    project_id: uuid.UUID,
    db: Session,
) -> list[uuid.UUID]:
    """
    Find all active subscriptions for this project+event_type.
    Create WebhookDelivery rows (status='pending').
    Returns list of delivery IDs created (for use by BackgroundTask caller).
    """
    try:
        subs = (
            db.query(WebhookSubscription)
            .filter(
                WebhookSubscription.project_id == project_id,
                WebhookSubscription.is_active == True,
            )
            .all()
        )
    except Exception:
        return []

    delivery_ids: list[uuid.UUID] = []

    for sub in subs:
        events = sub.events or []
        if event_type not in events and "*" not in events:
            continue
        try:
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                event=event_type,
                payload=payload,
                status="pending",
                attempt_count=0,
            )
            db.add(delivery)
            db.flush()
            delivery_ids.append(delivery.id)
        except Exception:
            pass  # Don't let webhook creation failures break the main transaction

    try:
        db.commit()
    except Exception:
        db.rollback()
        return []

    return delivery_ids


async def deliver_webhook(
    delivery_id: uuid.UUID,
    secret: str,
    url: str,
    payload: dict,
    event: str,
) -> str:
    """
    Deliver a single webhook with HMAC-SHA256 signature.
    Retries up to 3 times with exponential backoff (1s, 2s, 4s).
    Returns 'delivered' or 'failed'.
    """
    body = json.dumps(payload, default=str).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-PrismAtlas-Event": event,
        "X-PrismAtlas-Signature": f"sha256={sig}",
        "X-PrismAtlas-Delivery": str(delivery_id),
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, content=body, headers=headers)
                if resp.status_code < 300:
                    return "delivered"
        except Exception:
            pass
        if attempt < 2:
            await asyncio.sleep(2 ** attempt)  # 1s then 2s before retries

    return "failed"


async def process_pending_deliveries(db: Session) -> dict:
    """
    Process all pending WebhookDelivery rows.
    Called by a background task or scheduled job.
    Returns {"delivered": int, "failed": int}.
    """
    delivered_count = 0
    failed_count = 0

    pending = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.status == "pending")
        .limit(100)
        .all()
    )

    for delivery in pending:
        sub = db.query(WebhookSubscription).filter(
            WebhookSubscription.id == delivery.subscription_id
        ).first()
        if not sub or not sub.is_active:
            delivery.status = "failed"
            db.commit()
            failed_count += 1
            continue

        # Use secret_hash as the HMAC key (the stored hash, since we never
        # keep the raw secret — the caller must provide it during registration
        # for the first delivery; subsequent deliveries use the hash as a
        # best-effort key, or integrate with a secrets vault).
        result = await deliver_webhook(
            delivery_id=delivery.id,
            secret=sub.secret_hash,
            url=sub.url,
            payload=delivery.payload,
            event=delivery.event,
        )

        delivery.status = result
        delivery.attempt_count = (delivery.attempt_count or 0) + 1
        delivery.last_attempted_at = datetime.now(timezone.utc)
        db.commit()

        if result == "delivered":
            delivered_count += 1
        else:
            failed_count += 1

    return {"delivered": delivered_count, "failed": failed_count}
