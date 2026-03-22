"""
Bulk operations API — up to 10,000 objects per request.
Uses SQLAlchemy bulk_insert_mappings for performance.

Readiness evaluation is DEFERRED — call POST /projects/{id}/readiness/recompute-all
after a bulk insert to catch up.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.object import Object
from app.models.workflow import TaskInstance

router = APIRouter(prefix="/projects", tags=["bulk"])

MAX_ROWS = 10_000


class BulkObjectCreate(BaseModel):
    objects: list[dict[str, Any]]  # list of object field dicts, up to 10,000


class BulkResult(BaseModel):
    created: int
    skipped: int
    errors: list[dict[str, Any]]  # [{"row": N, "reason": "..."}]


@router.post("/{project_id}/bulk/objects", response_model=BulkResult)
def bulk_create_objects(
    project_id: uuid.UUID,
    body: BulkObjectCreate,
    db: Session = Depends(get_db),
):
    """Bulk create up to 10,000 objects. Readiness evaluation is deferred."""
    if len(body.objects) > MAX_ROWS:
        raise HTTPException(400, f"Maximum {MAX_ROWS} objects per request")

    errors: list[dict] = []
    mappings: list[dict] = []

    for i, obj_data in enumerate(body.objects):
        try:
            mapping = dict(obj_data)
            mapping["project_id"] = str(project_id)
            mapping.setdefault("id", str(uuid.uuid4()))
            mapping.setdefault("status", "active")
            # Ensure required fields
            if not mapping.get("name"):
                raise ValueError("name is required")
            if not mapping.get("object_type"):
                raise ValueError("object_type is required")
            mappings.append(mapping)
        except Exception as exc:
            errors.append({"row": i, "reason": str(exc)})

    if mappings:
        try:
            db.bulk_insert_mappings(Object, mappings)
            db.commit()
        except Exception as exc:
            db.rollback()
            errors.append({"row": -1, "reason": f"Bulk insert failed: {exc}"})
            return BulkResult(created=0, skipped=len(mappings), errors=errors)

    return BulkResult(created=len(mappings), skipped=0, errors=errors)


@router.patch("/{project_id}/bulk/objects", response_model=BulkResult)
def bulk_update_objects(
    project_id: uuid.UUID,
    body: dict[str, Any],
    db: Session = Depends(get_db),
):
    """Bulk update objects.

    Request body: {"object_ids": ["<uuid>", ...], "fields": {"status": "active", ...}}
    """
    object_ids = body.get("object_ids", [])
    fields = body.get("fields", {})

    if not object_ids:
        raise HTTPException(400, "object_ids is required")
    if not fields:
        raise HTTPException(400, "fields is required")
    if len(object_ids) > MAX_ROWS:
        raise HTTPException(400, f"Maximum {MAX_ROWS} object_ids per request")

    # Guard: do not allow overwriting project_id or id
    fields.pop("id", None)
    fields.pop("project_id", None)

    try:
        db.query(Object).filter(
            Object.id.in_(object_ids),
            Object.project_id == project_id,
        ).update(fields, synchronize_session=False)
        db.commit()
    except Exception as exc:
        db.rollback()
        return BulkResult(created=0, skipped=0, errors=[{"row": -1, "reason": str(exc)}])

    return BulkResult(created=0, skipped=0, errors=[])


@router.post("/{project_id}/bulk/task-status", response_model=BulkResult)
def bulk_complete_tasks(
    project_id: uuid.UUID,
    body: dict[str, Any],
    db: Session = Depends(get_db),
):
    """Bulk complete tasks.

    Request body: {"task_ids": ["<uuid>", ...], "completed_by": "name", "notes": "..."}
    """
    task_ids = body.get("task_ids", [])
    completed_by = body.get("completed_by", "bulk")
    notes = body.get("notes")

    if not task_ids:
        raise HTTPException(400, "task_ids is required")
    if len(task_ids) > MAX_ROWS:
        raise HTTPException(400, f"Maximum {MAX_ROWS} task_ids per request")

    now = datetime.now(timezone.utc)
    update_fields: dict[str, Any] = {
        "status": "complete",
        "completed_at": now,
        "completed_by": completed_by,
    }
    if notes is not None:
        update_fields["notes"] = notes

    try:
        count = (
            db.query(TaskInstance)
            .filter(TaskInstance.id.in_(task_ids))
            .update(update_fields, synchronize_session=False)
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        return BulkResult(created=0, skipped=0, errors=[{"row": -1, "reason": str(exc)}])

    return BulkResult(created=count, skipped=0, errors=[])
