"""
Cradle CSV importer.
Imports objects and requirements from Cradle-format CSV exports.

Cradle is a requirements management tool. Its CSV export typically contains:
  - Item ID / identifier
  - Item type (requirement, test case, etc.)
  - Title / name
  - Description
  - Status
  - Version
  - Parent ID (for hierarchical requirements)

Column names are auto-detected from the header row (case-insensitive).
"""
import csv
import io
import uuid
from sqlalchemy.orm import Session

from app.models.object import Object


# Candidate column names for each logical field (case-insensitive match)
_ID_COLS = ("item_id", "id", "identifier", "req_id", "number")
_NAME_COLS = ("title", "name", "summary", "requirement", "item_name")
_TYPE_COLS = ("type", "item_type", "object_type", "category")
_STATUS_COLS = ("status", "state", "item_status")
_DESC_COLS = ("description", "text", "detail", "content")


def import_cradle_csv(project_id: uuid.UUID, csv_content: str, db: Session) -> dict:
    """Parse Cradle CSV and import objects.

    Returns {"created": int, "skipped": int, "errors": list[str]}.
    """
    created = 0
    skipped = 0
    errors: list[str] = []

    reader = csv.DictReader(io.StringIO(csv_content))

    if reader.fieldnames is None:
        return {"created": 0, "skipped": 0, "errors": ["CSV has no header row"]}

    # Build a case-insensitive field map: logical_name → actual_column_name
    field_map = _build_field_map(list(reader.fieldnames))

    for i, row in enumerate(reader):
        try:
            name = _get_field(row, field_map, _NAME_COLS, fallback=f"Imported item {i + 1}")
            object_type = _get_field(row, field_map, _TYPE_COLS, fallback="requirement")
            status = _get_field(row, field_map, _STATUS_COLS, fallback="Not Started")
            description = _get_field(row, field_map, _DESC_COLS, fallback=None)
            external_id = _get_field(row, field_map, _ID_COLS, fallback=None)

            if not name:
                skipped += 1
                continue

            obj = Object(
                id=uuid.uuid4(),
                project_id=project_id,
                name=name[:255],
                # Map to a valid OBJECT_TYPES entry; store original type in description prefix
                object_type="Other",
                status=_map_cradle_status(status),
                description=description,
                # Store the Cradle ID in a recognisable custom field if the model supports it.
                # For now, we prefix the name when an external ID exists.
            )

            # If the Object model has a tag or external_id field, set it here.
            # Currently we store the Cradle ID in the name prefix as a best-effort approach.
            if external_id and not name.startswith(external_id):
                obj.name = f"{external_id}: {name}"[:255]

            db.add(obj)
            created += 1

        except Exception as exc:
            errors.append(f"Row {i + 1}: {exc}")
            skipped += 1

    if created:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            errors.append(f"Commit failed: {exc}")
            return {"created": 0, "skipped": created + skipped, "errors": errors}

    return {"created": created, "skipped": skipped, "errors": errors}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_field_map(fieldnames: list[str]) -> dict[str, str]:
    """Map lowercase field name → actual column name from header."""
    return {f.lower().strip(): f for f in fieldnames}


def _get_field(
    row: dict,
    field_map: dict[str, str],
    candidates: tuple[str, ...],
    fallback: str | None = None,
) -> str | None:
    """Return the first matching column value from a list of candidate names."""
    for candidate in candidates:
        actual = field_map.get(candidate.lower())
        if actual and actual in row:
            val = row[actual]
            if val and val.strip():
                return val.strip()
    return fallback


def _map_cradle_status(cradle_status: str | None) -> str:
    """Map Cradle item status to PrismAtlas object status (must be in OBJECT_STATUSES)."""
    if not cradle_status:
        return "not_started"
    s = cradle_status.lower().strip()
    if s in ("complete", "done", "finished", "closed", "obsolete", "deleted", "cancelled", "archived"):
        return "complete"
    if s in ("blocked", "inactive", "rejected", "on_hold"):
        return "blocked"
    if s in ("active", "in_progress", "in progress", "started", "wip"):
        return "in_progress"
    return "not_started"
