"""
P6 XER importer.
Parses XER format and creates Object + WorkflowInstance + TaskInstance rows.

XER format uses:
  %T  <TABLE_NAME>   — start of table section
  %F  <f1>\t<f2>...  — field names
  %R  <v1>\t<v2>...  — data rows
  %E               — end of table section

import_source is stored in WorkflowInstance.overridden_fields as
  {"import_source": "p6"}
since workflow_instances does not have a dedicated metadata column.
"""
import uuid
from sqlalchemy.orm import Session

from app.models.object import Object
from app.models.workflow import WorkflowInstance, StageInstance, TaskInstance
from app.models.dependency import DependencyRule


def import_xer(project_id: uuid.UUID, xer_content: str, db: Session) -> dict:
    """Parse XER content and import into project.

    Returns {"created": int, "skipped": int, "errors": list[str]}.
    """
    created = 0
    skipped = 0
    errors: list[str] = []

    try:
        sections = _parse_xer_sections(xer_content)
    except Exception as exc:
        return {"created": 0, "skipped": 0, "errors": [f"XER parse failure: {exc}"]}

    # ── TASK → Object + WorkflowInstance + StageInstance + TaskInstance ───────
    tasks_section = sections.get("TASK", [])
    task_rows_by_id: dict[str, dict] = {}

    # Resolve or create a minimal WorkflowTemplateVersion for imported tasks.
    # We look for a template version already in DB; if none, we skip the import
    # of instances (objects will still be created).
    from app.models.workflow import WorkflowTemplateVersion, WorkflowTemplate
    template_version = (
        db.query(WorkflowTemplateVersion)
        .join(WorkflowTemplate)
        .filter(WorkflowTemplate.applies_to_type == "object")
        .order_by(WorkflowTemplateVersion.version_number.desc())
        .first()
    )

    for row in tasks_section:
        task_code = row.get("task_code") or row.get("task_id", "")
        task_name = row.get("task_name", task_code)

        # Create Object row
        try:
            obj = Object(
                id=uuid.uuid4(),
                project_id=project_id,
                name=task_name,
                object_type="Other",   # valid OBJECT_TYPES entry for imports
                status="active",
            )
            db.add(obj)
            db.flush()  # get ID before creating workflow instance
            task_rows_by_id[task_code] = {"object_id": obj.id, "row": row}

            # Create WorkflowInstance if we have a template
            if template_version:
                wi = WorkflowInstance(
                    id=uuid.uuid4(),
                    entity_type="object",
                    entity_id=obj.id,
                    template_version_id=template_version.id,
                    status="active",
                    overridden_fields={"import_source": "p6", "p6_task_code": task_code},
                )
                db.add(wi)
                db.flush()

                # Create a single default stage + task from XER data
                stage = StageInstance(
                    id=uuid.uuid4(),
                    workflow_instance_id=wi.id,
                    stage_key="imported",
                    stage_name="Imported from P6",
                    stage_order=1,
                    status="active",
                )
                db.add(stage)
                db.flush()

                dur = _parse_duration_hr(row.get("target_drtn_hr_cnt", "8"))
                status = _map_p6_status(row.get("status_code", ""))
                ti = TaskInstance(
                    id=uuid.uuid4(),
                    stage_instance_id=stage.id,
                    task_key=task_code,
                    task_name=task_name,
                    task_order=1,
                    is_mandatory=True,
                    status=status,
                    duration_days=max(1, dur // 8),
                    effort_hours=float(row.get("target_work_qty", dur)),
                )
                db.add(ti)

            created += 1
        except Exception as exc:
            db.rollback()
            errors.append(f"Task {task_code}: {exc}")
            skipped += 1
            continue

    # ── TASKPRED → DependencyRule ─────────────────────────────────────────────
    preds_section = sections.get("TASKPRED", [])
    for row in preds_section:
        pred_code = row.get("pred_task_id", "")
        succ_code = row.get("task_id", "")
        src_info = task_rows_by_id.get(pred_code)
        tgt_info = task_rows_by_id.get(succ_code)
        if src_info and tgt_info:
            try:
                lag_hr = float(row.get("lag_hr_cnt", 0) or 0)
                rule = DependencyRule(
                    id=uuid.uuid4(),
                    name=f"{pred_code}→{succ_code}",
                    source_entity_type="object",
                    source_entity_id=src_info["object_id"],
                    target_entity_type="object",
                    target_entity_id=tgt_info["object_id"],
                    condition={"type": "finish_to_start"},
                    is_mandatory=True,
                    lag_days=int(lag_hr / 8) if lag_hr else 0,
                )
                db.add(rule)
            except Exception as exc:
                errors.append(f"Predecessor {pred_code}→{succ_code}: {exc}")

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        errors.append(f"Commit failed: {exc}")
        return {"created": 0, "skipped": len(tasks_section), "errors": errors}

    return {"created": created, "skipped": skipped, "errors": errors}


# ── XER parser ────────────────────────────────────────────────────────────────

def _parse_xer_sections(content: str) -> dict[str, list[dict]]:
    """Parse XER content into a dict of table_name → list of row dicts."""
    sections: dict[str, list[dict]] = {}
    current_table: str | None = None
    current_fields: list[str] = []

    for line in content.splitlines():
        line = line.rstrip("\r")
        if not line:
            continue
        if line.startswith("%T"):
            current_table = line.split("\t", 1)[1].strip() if "\t" in line else line[2:].strip()
            current_fields = []
            sections[current_table] = []
        elif line.startswith("%F") and current_table:
            parts = line.split("\t")
            current_fields = [p.strip() for p in parts[1:]]
        elif line.startswith("%R") and current_table and current_fields:
            parts = line.split("\t")
            values = parts[1:]
            row = dict(zip(current_fields, values))
            sections[current_table].append(row)
        elif line.startswith("%E"):
            current_table = None
            current_fields = []

    return sections


def _parse_duration_hr(value: str) -> int:
    """Parse duration in hours from XER string (may be float string)."""
    try:
        return max(1, int(float(str(value).strip())))
    except (ValueError, TypeError):
        return 8


def _map_p6_status(p6_status: str) -> str:
    """Map P6 task status code to PrismAtlas task status."""
    mapping = {
        "TK_Complete": "complete",
        "TK_Active": "in_progress",
        "TK_NotStart": "pending",
    }
    return mapping.get(p6_status.strip(), "pending")
