"""
Audit log utility — NFR-7.3.

Provides a single function to record an immutable audit entry.
user_id and project_id may be None for system-initiated actions.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def audit_log(
    db: Session,
    user_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    field: str | None = None,
    old: Any = None,
    new: Any = None,
    project_id: uuid.UUID | None = None,
) -> AuditLog:
    """
    Create and flush (but do not commit) an AuditLog row.

    Callers are responsible for the surrounding commit so that the audit entry
    and the business change land in the same transaction.

    Args:
        db:           SQLAlchemy session.
        user_id:      UUID of the acting user, or None for system actions.
        entity_type:  Table/domain name, e.g. 'workflow_instance', 'task_instance'.
        entity_id:    UUID of the affected row.
        action:       Short verb: 'created', 'updated', 'deleted', 'template_propagated', etc.
        field:        Optional field name for field-level granularity.
        old:          Previous value (will be wrapped in {"v": old} if not already a dict).
        new:          New value (same wrapping).
        project_id:   Optional project context for scoped queries.

    Returns:
        The (unflushed AuditLog instance — id is already assigned via default).
    """

    def _wrap(val: Any) -> dict | None:
        if val is None:
            return None
        if isinstance(val, dict):
            return val
        return {"v": val}

    entry = AuditLog(
        project_id=project_id,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        field_name=field,
        old_value=_wrap(old),
        new_value=_wrap(new),
        timestamp=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.flush()
    return entry
