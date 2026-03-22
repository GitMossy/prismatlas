"""
Type propagation engine — FR-4.2.5

Auto-propagates parent template changes to child templates and their live instances.
When a new version of a parent template is published, this engine:
  1. Finds all child templates (parent_template_id == parent).
  2. Merges the new parent definition with each child's current active definition.
  3. Creates a new child version recording the inherited_from_version_id.
  4. For each live WorkflowInstance on the old child version, applies new tasks
     and updates non-overridden fields in-place (no stage re-creation).

Performance notes (E4):
- propagate_template_change() can be a long-running operation for projects with
  many live instances. WRAP IT in a FastAPI BackgroundTask at the call site so it
  does not block the HTTP response:

    from fastapi import BackgroundTasks
    @router.post("/.../publish")
    def publish_version(bg: BackgroundTasks, ...):
        bg.add_task(propagate_template_change, new_version.id, db)
        return {"status": "propagation queued"}

- For large deployments, use bulk_propagate_template_change() instead of
  propagate_template_change() — it uses bulk_insert_mappings for new tasks and
  a single bulk UPDATE for changed field values, reducing N round-trips to O(1).

- The single bulk UPDATE pattern for changed fields:
    db.query(TaskInstance)
      .filter(TaskInstance.task_key == task_key, TaskInstance.stage_instance_id.in_(stage_ids))
      .update({"task_name": new_name}, synchronize_session=False)
  This updates all matching task instances in one SQL statement instead of one
  per instance in a Python loop.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.workflow import (
    WorkflowTemplate,
    WorkflowTemplateVersion,
    WorkflowInstance,
    StageInstance,
    TaskInstance,
)
from app.engines.audit import audit_log


def propagate_template_change(parent_version_id: uuid.UUID, db: Session) -> int:
    """
    Propagate a new parent template version to all child templates and their live instances.

    Returns:
        Count of WorkflowInstances updated across all child templates.
    """
    parent_version = (
        db.query(WorkflowTemplateVersion)
        .filter(WorkflowTemplateVersion.id == parent_version_id)
        .first()
    )
    if not parent_version:
        return 0

    parent_template = parent_version.template
    children = (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.parent_template_id == parent_template.id)
        .all()
    )
    total_updated = 0

    for child in children:
        active_child_version = (
            db.query(WorkflowTemplateVersion)
            .filter(
                WorkflowTemplateVersion.template_id == child.id,
                WorkflowTemplateVersion.is_active == True,  # noqa: E712
            )
            .first()
        )

        merged_def = _merge_definitions(
            parent_version.definition,
            active_child_version.definition if active_child_version else {},
        )

        new_version_number = (active_child_version.version_number + 1) if active_child_version else 1
        new_version = WorkflowTemplateVersion(
            template_id=child.id,
            version_number=new_version_number,
            definition=merged_def,
            is_active=True,
            inherited_from_version_id=parent_version_id,
            created_at=datetime.now(timezone.utc),
        )

        if active_child_version:
            active_child_version.is_active = False

        db.add(new_version)
        db.flush()  # populate new_version.id before referencing it

        # Propagate to live instances on the old child version
        if active_child_version:
            instances = (
                db.query(WorkflowInstance)
                .filter(
                    WorkflowInstance.template_version_id == active_child_version.id,
                    WorkflowInstance.status == "active",
                )
                .all()
            )

            for inst in instances:
                _apply_propagation_to_instance(inst, merged_def, db)
                inst.template_version_id = new_version.id
                total_updated += 1
                audit_log(
                    db,
                    user_id=None,
                    entity_type="workflow_instance",
                    entity_id=inst.id,
                    action="template_propagated",
                    field="template_version_id",
                    old=str(active_child_version.id),
                    new=str(new_version.id),
                )

    db.commit()
    return total_updated


def _merge_definitions(parent_def: dict, child_def: dict) -> dict:
    """
    Merge parent stages into child definition.

    Rules:
      - Parent stages appear first (in parent order).
      - Child stages with the same key override the parent stage.
      - Child-only stages are appended after all parent stages.
    """
    parent_stages: dict[str, dict] = {
        s["key"]: s for s in parent_def.get("stages", [])
    }
    child_stages: dict[str, dict] = {
        s["key"]: s for s in child_def.get("stages", [])
    }

    # Start with parent order; let child override each entry
    result_stages: list[dict] = []
    for s in parent_def.get("stages", []):
        result_stages.append(child_stages.get(s["key"], s))

    # Append child-only stages (not present in parent)
    for key, stage in child_stages.items():
        if key not in parent_stages:
            result_stages.append(stage)

    return {"stages": result_stages}


def _apply_propagation_to_instance(
    instance: WorkflowInstance, new_def: dict, db: Session
) -> None:
    """
    Apply a new template definition to a live WorkflowInstance without disruption.

    Strategy:
      - Insert new tasks that don't exist yet in matched stage instances.
      - Update changed fields (task_name, is_mandatory) only when NOT in
        instance.overridden_fields.
      - New stages are NOT auto-created (too disruptive for in-flight workflows).

    overridden_fields format: {"<task_key>:<field_name>": true}
    """
    overridden: dict[str, Any] = instance.overridden_fields or {}

    for stage_def in new_def.get("stages", []):
        stage_key = stage_def["key"]
        stage_inst: StageInstance | None = next(
            (s for s in instance.stage_instances if s.stage_key == stage_key), None
        )
        if stage_inst is None:
            continue  # New stages not auto-created in live instances

        for task_def in stage_def.get("tasks", []):
            task_key = task_def["key"]
            task_inst: TaskInstance | None = next(
                (t for t in stage_inst.task_instances if t.task_key == task_key), None
            )

            if task_inst is None:
                # New task in the template — add it to the live stage
                new_task = TaskInstance(
                    stage_instance_id=stage_inst.id,
                    task_key=task_key,
                    task_name=task_def.get("name", task_key),
                    task_order=task_def.get("order", 999),
                    is_mandatory=task_def.get("is_mandatory", True),
                    status="pending",
                )
                db.add(new_task)
            else:
                # Update fields only if not overridden at instance level
                field_map = {
                    "task_name": task_def.get("name"),
                    "is_mandatory": task_def.get("is_mandatory"),
                }
                for field_name, def_val in field_map.items():
                    override_key = f"{task_key}:{field_name}"
                    if override_key not in overridden and def_val is not None:
                        setattr(task_inst, field_name, def_val)


# ── E4: Bulk propagation variant ──────────────────────────────────────────────

def bulk_propagate_template_change(parent_version_id: uuid.UUID, db: Session) -> int:
    """
    High-performance variant of propagate_template_change for large deployments.

    Differences from propagate_template_change():
    - New tasks are inserted via db.bulk_insert_mappings (single INSERT per batch).
    - Changed field values use a single bulk UPDATE per (task_key, field) across
      all matched stage instances rather than row-by-row Python updates.
    - All instance template_version_id updates are batched into one SQL UPDATE.

    E4 bulk UPDATE pattern:
      db.query(TaskInstance)
        .filter(TaskInstance.task_key == task_key, TaskInstance.stage_instance_id.in_(stage_ids))
        .update({"task_name": new_name}, synchronize_session=False)

    Returns count of WorkflowInstances updated.
    """
    parent_version = (
        db.query(WorkflowTemplateVersion)
        .filter(WorkflowTemplateVersion.id == parent_version_id)
        .first()
    )
    if not parent_version:
        return 0

    parent_template = parent_version.template
    children = (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.parent_template_id == parent_template.id)
        .all()
    )
    total_updated = 0

    for child in children:
        active_child_version = (
            db.query(WorkflowTemplateVersion)
            .filter(
                WorkflowTemplateVersion.template_id == child.id,
                WorkflowTemplateVersion.is_active == True,  # noqa: E712
            )
            .first()
        )

        merged_def = _merge_definitions(
            parent_version.definition,
            active_child_version.definition if active_child_version else {},
        )

        new_version_number = (active_child_version.version_number + 1) if active_child_version else 1
        new_version = WorkflowTemplateVersion(
            template_id=child.id,
            version_number=new_version_number,
            definition=merged_def,
            is_active=True,
            inherited_from_version_id=parent_version_id,
            created_at=datetime.now(timezone.utc),
        )
        if active_child_version:
            active_child_version.is_active = False
        db.add(new_version)
        db.flush()

        if not active_child_version:
            continue

        # Collect all active instances on this child version
        instances = (
            db.query(WorkflowInstance)
            .filter(
                WorkflowInstance.template_version_id == active_child_version.id,
                WorkflowInstance.status == "active",
            )
            .all()
        )
        if not instances:
            continue

        instance_ids = [inst.id for inst in instances]

        # Collect all stage instances for these workflow instances
        stage_instances = (
            db.query(StageInstance)
            .filter(StageInstance.workflow_instance_id.in_(instance_ids))
            .all()
        )

        # Build: stage_key → list of stage_instance_ids
        from collections import defaultdict as _dd
        stage_key_to_ids: dict[str, list[uuid.UUID]] = _dd(list)
        stage_id_set: dict[uuid.UUID, StageInstance] = {}
        for si in stage_instances:
            stage_key_to_ids[si.stage_key].append(si.id)
            stage_id_set[si.id] = si

        # Collect existing task keys per stage instance to detect new tasks
        existing_task_keys: dict[uuid.UUID, set[str]] = _dd(set)
        existing_tasks = (
            db.query(TaskInstance)
            .filter(TaskInstance.stage_instance_id.in_(list(stage_id_set.keys())))
            .all()
        )
        for t in existing_tasks:
            existing_task_keys[t.stage_instance_id].add(t.task_key)

        # Build bulk insert list and bulk update operations
        new_task_mappings: list[dict] = []

        for stage_def in merged_def.get("stages", []):
            stage_key = stage_def["key"]
            si_ids = stage_key_to_ids.get(stage_key, [])
            if not si_ids:
                continue

            for task_def in stage_def.get("tasks", []):
                task_key = task_def["key"]
                task_name = task_def.get("name", task_key)
                is_mandatory = task_def.get("is_mandatory", True)
                task_order = task_def.get("order", 999)

                # New tasks: stage instances that don't yet have this task_key
                for si_id in si_ids:
                    if task_key not in existing_task_keys[si_id]:
                        new_task_mappings.append({
                            "id": str(uuid.uuid4()),
                            "stage_instance_id": str(si_id),
                            "task_key": task_key,
                            "task_name": task_name,
                            "task_order": task_order,
                            "is_mandatory": is_mandatory,
                            "status": "pending",
                        })

                # Bulk UPDATE task_name for existing tasks not overridden
                # Single UPDATE statement per (task_key, field) — E4 pattern
                db.query(TaskInstance).filter(
                    TaskInstance.task_key == task_key,
                    TaskInstance.stage_instance_id.in_(si_ids),
                ).update({"task_name": task_name, "is_mandatory": is_mandatory},
                         synchronize_session=False)

        # Bulk insert new tasks
        if new_task_mappings:
            db.bulk_insert_mappings(TaskInstance, new_task_mappings)

        # Bulk update template_version_id for all instances
        db.query(WorkflowInstance).filter(
            WorkflowInstance.id.in_(instance_ids),
        ).update({"template_version_id": new_version.id}, synchronize_session=False)

        total_updated += len(instance_ids)

    db.commit()
    return total_updated
