"""
Readiness calculation engine.

Computes three-dimensional readiness for any entity (object or document):
  - technical_readiness  : mandatory workflow tasks completed
  - document_readiness   : mandatory linked documents in required state
  - stage_readiness      : dependency rules satisfied

Overall readiness = average of all three dimensions.
FAT / SAT gates are evaluated separately as hard boolean checks.

Readiness is ALWAYS derived — never manually set (invariant #7).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.class_definition import ClassDefinition
from app.models.dependency import DependencyRule, Relationship
from app.models.document import Document
from app.models.object import Object
from app.models.readiness import ReadinessEvaluation
from app.models.workflow import WorkflowInstance, StageInstance, TaskInstance, WorkflowTemplateVersion
from app.engines.dependency import evaluate_condition

# Stage keys that must be complete for FAT / SAT gates
FAT_GATE_STAGE = "fat_prep"
SAT_GATE_STAGE = "sat_prep"
FAT_EXECUTION_TASK = "fat_execution"


def evaluate_entity(entity_type: str, entity_id: uuid.UUID, db: Session) -> ReadinessEvaluation:
    """
    Full readiness evaluation for one entity. Persists and returns a
    ReadinessEvaluation row. Call this whenever state changes.
    """
    blockers: list[dict] = []

    technical_readiness = _technical_readiness(entity_type, entity_id, db, blockers)
    document_readiness = _document_readiness(entity_type, entity_id, db, blockers)
    stage_readiness = _stage_readiness(entity_type, entity_id, db, blockers)

    overall_readiness = round((technical_readiness + document_readiness + stage_readiness) / 3, 4)

    ready_for_fat = _check_fat_gate(entity_type, entity_id, document_readiness, blockers, db)
    ready_for_sat = _check_sat_gate(entity_type, entity_id, ready_for_fat, db)

    next_action = _next_action(blockers, technical_readiness, document_readiness, stage_readiness)

    # E2: Mark all previous evaluations for this entity as not current before
    # adding the new one. This keeps queries efficient:
    #   SELECT * FROM readiness_evaluations WHERE entity_id=? AND is_current=TRUE
    db.query(ReadinessEvaluation).filter(
        ReadinessEvaluation.entity_id == entity_id,
        ReadinessEvaluation.entity_type == entity_type,
        ReadinessEvaluation.is_current == True,
    ).update({"is_current": False}, synchronize_session=False)

    evaluation = ReadinessEvaluation(
        entity_type=entity_type,
        entity_id=entity_id,
        technical_readiness=technical_readiness,
        document_readiness=document_readiness,
        stage_readiness=stage_readiness,
        overall_readiness=overall_readiness,
        ready_for_fat=ready_for_fat,
        ready_for_sat=ready_for_sat,
        blockers=blockers,
        next_action=next_action,
        evaluated_at=datetime.now(timezone.utc),
        is_current=True,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


# ---------------------------------------------------------------------------
# Dimension 1: Technical Readiness
# ---------------------------------------------------------------------------

def _technical_readiness(
    entity_type: str,
    entity_id: uuid.UUID,
    db: Session,
    blockers: list[dict],
) -> float:
    """% of mandatory workflow tasks that are complete."""
    instance = (
        db.query(WorkflowInstance)
        .filter(
            WorkflowInstance.entity_id == entity_id,
            WorkflowInstance.entity_type == entity_type,
        )
        .order_by(WorkflowInstance.created_at.desc())
        .first()
    )
    if not instance:
        return 1.0  # No workflow assigned = no technical requirement

    tasks = (
        db.query(TaskInstance)
        .join(StageInstance)
        .filter(
            StageInstance.workflow_instance_id == instance.id,
            TaskInstance.is_mandatory == True,
        )
        .all()
    )
    if not tasks:
        return 1.0

    incomplete = [t for t in tasks if t.status != "complete"]
    for task in incomplete:
        stage = db.query(StageInstance).filter(StageInstance.id == task.stage_instance_id).first()
        blockers.append({
            "type": "task",
            "entity_id": str(task.id),
            "entity_name": task.task_name,
            "reason": f"Task '{task.task_name}' in stage '{stage.stage_name if stage else '?'}' is not complete",
            "severity": "blocking",
        })

    return round(1 - len(incomplete) / len(tasks), 4)


# ---------------------------------------------------------------------------
# Dimension 2: Document Readiness
# ---------------------------------------------------------------------------

def _document_readiness(
    entity_type: str,
    entity_id: uuid.UUID,
    db: Session,
    blockers: list[dict],
) -> float:
    """% of mandatory linked documents that are in Approved state."""
    mandatory_rels = (
        db.query(Relationship)
        .filter(
            Relationship.source_entity_id == entity_id,
            Relationship.target_entity_type == "document",
            Relationship.is_mandatory == True,
        )
        .all()
    )
    if not mandatory_rels:
        return 1.0

    unsatisfied = 0
    for rel in mandatory_rels:
        doc = db.query(Document).filter(Document.id == rel.target_entity_id).first()
        if not doc:
            blockers.append({
                "type": "document",
                "entity_id": str(rel.target_entity_id),
                "entity_name": "Unknown document",
                "reason": f"Mandatory linked document {rel.target_entity_id} not found",
                "severity": "blocking",
            })
            unsatisfied += 1
        elif doc.status != "Approved":
            blockers.append({
                "type": "document",
                "entity_id": str(doc.id),
                "entity_name": doc.name,
                "reason": f"Document '{doc.name}' is '{doc.status}' — must be 'Approved'",
                "severity": "blocking",
            })
            unsatisfied += 1

    return round(1 - unsatisfied / len(mandatory_rels), 4)


# ---------------------------------------------------------------------------
# Dimension 3: Stage / Dependency Readiness
# ---------------------------------------------------------------------------

def _stage_readiness(
    entity_type: str,
    entity_id: uuid.UUID,
    db: Session,
    blockers: list[dict],
) -> float:
    """% of applicable dependency rules (+ class gate) that are satisfied."""
    # Rules that target this specific entity OR all entities of this type
    rules = (
        db.query(DependencyRule)
        .filter(
            DependencyRule.source_entity_type == entity_type,
            DependencyRule.source_entity_id.in_([entity_id, None]),
        )
        .all()
    )

    mandatory_rules = [r for r in rules if r.is_mandatory and r.target_entity_id is not None]
    total_mandatory = len(mandatory_rules)
    unsatisfied = 0

    for rule in rules:
        # If rule has no specific target entity, skip instance-level evaluation
        if rule.target_entity_id is None:
            continue

        satisfied, reason = evaluate_condition(
            rule.condition,
            rule.target_entity_type,
            rule.target_entity_id,
            db,
        )
        if not satisfied:
            blockers.append({
                "type": "dependency",
                "entity_id": str(rule.target_entity_id),
                "entity_name": rule.name,
                "reason": reason,
                "severity": "blocking" if rule.is_mandatory else "warning",
            })
            if rule.is_mandatory:
                unsatisfied += 1

    # Class-gate: object linked to a ClassDefinition must have it configured
    if entity_type == "object":
        obj = db.query(Object).filter(Object.id == entity_id).first()
        if obj and obj.class_definition_id:
            total_mandatory += 1
            cls = db.query(ClassDefinition).filter(
                ClassDefinition.id == obj.class_definition_id
            ).first()
            if not cls:
                unsatisfied += 1
                blockers.append({
                    "type": "class",
                    "entity_id": str(obj.class_definition_id),
                    "entity_name": "Unknown class",
                    "reason": "Linked library class not found",
                    "severity": "blocking",
                })
            elif not cls.workflow_template_id:
                unsatisfied += 1
                blockers.append({
                    "type": "class",
                    "entity_id": str(cls.id),
                    "entity_name": cls.name,
                    "reason": f"Library class '{cls.name}' has no workflow template — configure the class before area objects can proceed",
                    "severity": "blocking",
                })
            else:
                active_ver = db.query(WorkflowTemplateVersion).filter(
                    WorkflowTemplateVersion.template_id == cls.workflow_template_id,
                    WorkflowTemplateVersion.is_active.is_(True),
                ).first()
                if not active_ver:
                    unsatisfied += 1
                    blockers.append({
                        "type": "class",
                        "entity_id": str(cls.id),
                        "entity_name": cls.name,
                        "reason": f"Library class '{cls.name}' workflow template has no active version",
                        "severity": "blocking",
                    })

    if total_mandatory == 0:
        return 1.0

    return round(1 - unsatisfied / total_mandatory, 4)


# ---------------------------------------------------------------------------
# FAT / SAT gate checks
# ---------------------------------------------------------------------------

def _check_fat_gate(
    entity_type: str,
    entity_id: uuid.UUID,
    document_readiness: float,
    blockers: list[dict],
    db: Session,
) -> bool:
    """
    FAT ready requires:
    1. All mandatory documents are Approved (document_readiness == 1.0)
    2. No blocking-severity blockers
    3. FAT prep stage complete (if workflow exists with that stage)
    """
    if document_readiness < 1.0:
        return False

    has_blocking = any(b["severity"] == "blocking" for b in blockers)
    if has_blocking:
        return False

    # Check FAT prep stage if workflow exists
    instance = (
        db.query(WorkflowInstance)
        .filter(
            WorkflowInstance.entity_id == entity_id,
            WorkflowInstance.entity_type == entity_type,
        )
        .order_by(WorkflowInstance.created_at.desc())
        .first()
    )
    if instance:
        fat_prep = (
            db.query(StageInstance)
            .filter(
                StageInstance.workflow_instance_id == instance.id,
                StageInstance.stage_key == FAT_GATE_STAGE,
            )
            .first()
        )
        if fat_prep and fat_prep.status != "complete":
            return False

    return True


def _check_sat_gate(
    entity_type: str,
    entity_id: uuid.UUID,
    ready_for_fat: bool,
    db: Session,
) -> bool:
    """
    SAT ready requires:
    1. FAT ready
    2. FAT execution task recorded with result 'PASS'
    """
    if not ready_for_fat:
        return False

    instance = (
        db.query(WorkflowInstance)
        .filter(
            WorkflowInstance.entity_id == entity_id,
            WorkflowInstance.entity_type == entity_type,
        )
        .order_by(WorkflowInstance.created_at.desc())
        .first()
    )
    if not instance:
        return False

    fat_task = (
        db.query(TaskInstance)
        .join(StageInstance)
        .filter(
            StageInstance.workflow_instance_id == instance.id,
            TaskInstance.task_key == FAT_EXECUTION_TASK,
        )
        .first()
    )
    if not fat_task:
        return False

    return fat_task.status == "complete" and fat_task.notes == "PASS"


# ---------------------------------------------------------------------------
# Next action
# ---------------------------------------------------------------------------

def _next_action(
    blockers: list[dict],
    technical: float,
    document: float,
    stage: float,
) -> str | None:
    if not blockers and technical == 1.0 and document == 1.0 and stage == 1.0:
        return "All readiness criteria met"

    # Prioritise the worst dimension
    if document < 1.0:
        doc_blockers = [b for b in blockers if b["type"] == "document"]
        if doc_blockers:
            return f"Get document approved: {doc_blockers[0]['entity_name']}"

    if stage < 1.0:
        dep_blockers = [b for b in blockers if b["type"] == "dependency"]
        if dep_blockers:
            return f"Resolve dependency: {dep_blockers[0]['reason']}"

    if technical < 1.0:
        task_blockers = [b for b in blockers if b["type"] == "task"]
        if task_blockers:
            return f"Complete task: {task_blockers[0]['entity_name']}"

    if blockers:
        return blockers[0]["reason"]

    return None
