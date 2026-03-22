"""
Dependency evaluation engine.

Evaluates a DependencyRule condition against the current live state of a target entity.
Returns (satisfied: bool, reason: str) — the reason is a human-readable explanation
of why the condition is NOT satisfied (empty string when satisfied).
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.object import Object
from app.models.workflow import WorkflowInstance, StageInstance


def evaluate_condition(
    condition: dict[str, Any],
    target_entity_type: str,
    target_entity_id: uuid.UUID,
    db: Session,
) -> tuple[bool, str]:
    """
    Evaluate a single dependency condition.

    Supported condition shapes:
      {"target_status": "Approved"}
          — target entity must be in the given status field

      {"target_stage_key": "fat_execution", "operator": "complete"}
          — target object must have completed the named stage

      {"target_task_result": "PASS", "task_key": "fat_execution"}
          — a specific task on the target object must be complete with notes == "PASS"
    """
    if target_entity_type == "document":
        return _evaluate_document_condition(condition, target_entity_id, db)

    if target_entity_type == "object":
        return _evaluate_object_condition(condition, target_entity_id, db)

    if target_entity_type == "stage":
        return _evaluate_stage_condition(condition, target_entity_id, db)

    return True, ""


def _evaluate_document_condition(
    condition: dict[str, Any],
    document_id: uuid.UUID,
    db: Session,
) -> tuple[bool, str]:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return False, f"Document {document_id} not found"

    required_status = condition.get("target_status")
    if required_status and doc.status != required_status:
        return (
            False,
            f"Document '{doc.name}' is '{doc.status}' — requires '{required_status}'",
        )

    return True, ""


def _evaluate_object_condition(
    condition: dict[str, Any],
    object_id: uuid.UUID,
    db: Session,
) -> tuple[bool, str]:
    obj = db.query(Object).filter(Object.id == object_id).first()
    if not obj:
        return False, f"Object {object_id} not found"

    # Check object-level status
    required_status = condition.get("target_status")
    if required_status and obj.status != required_status:
        return (
            False,
            f"Object '{obj.name}' is '{obj.status}' — requires '{required_status}'",
        )

    # Check that a specific stage has been completed
    required_stage_key = condition.get("target_stage_key")
    if required_stage_key:
        instance = (
            db.query(WorkflowInstance)
            .filter(
                WorkflowInstance.entity_id == object_id,
                WorkflowInstance.entity_type == "object",
            )
            .order_by(WorkflowInstance.created_at.desc())
            .first()
        )
        if not instance:
            return False, f"Object '{obj.name}' has no workflow — stage '{required_stage_key}' cannot be verified"

        stage = (
            db.query(StageInstance)
            .filter(
                StageInstance.workflow_instance_id == instance.id,
                StageInstance.stage_key == required_stage_key,
            )
            .first()
        )
        if not stage:
            return False, f"Object '{obj.name}' workflow has no stage '{required_stage_key}'"
        if stage.status != "complete":
            return (
                False,
                f"Object '{obj.name}' stage '{stage.stage_name}' is '{stage.status}' — must be complete",
            )

    # Check a specific task result (e.g. FAT execution must be PASS)
    required_task_result = condition.get("target_task_result")
    task_key = condition.get("task_key")
    if required_task_result and task_key:
        instance = (
            db.query(WorkflowInstance)
            .filter(
                WorkflowInstance.entity_id == object_id,
                WorkflowInstance.entity_type == "object",
            )
            .order_by(WorkflowInstance.created_at.desc())
            .first()
        )
        if not instance:
            return False, f"Object '{obj.name}' has no workflow — task result cannot be verified"

        from app.models.workflow import TaskInstance
        task = (
            db.query(TaskInstance)
            .join(StageInstance)
            .filter(
                StageInstance.workflow_instance_id == instance.id,
                TaskInstance.task_key == task_key,
            )
            .first()
        )
        if not task:
            return False, f"Object '{obj.name}' has no task '{task_key}'"
        if task.status != "complete":
            return False, f"Object '{obj.name}' task '{task.task_name}' is not complete"
        if task.notes != required_task_result:
            return (
                False,
                f"Object '{obj.name}' task '{task.task_name}' result is '{task.notes}' — requires '{required_task_result}'",
            )

    return True, ""


def _evaluate_stage_condition(
    condition: dict[str, Any],
    stage_id: uuid.UUID,
    db: Session,
) -> tuple[bool, str]:
    stage = db.query(StageInstance).filter(StageInstance.id == stage_id).first()
    if not stage:
        return False, f"Stage {stage_id} not found"
    if stage.status != "complete":
        return False, f"Stage '{stage.stage_name}' is '{stage.status}' — must be complete"
    return True, ""
