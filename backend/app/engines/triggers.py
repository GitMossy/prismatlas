"""
Re-evaluation trigger system.

Each function identifies which entities are affected by a state change,
then calls the readiness engine for each one.

Invariant #4: DependencyRule deletion must trigger re-evaluation of all
affected ReadinessEvaluations.

Webhook events dispatched on state changes:
  task.completed          — on_task_completed
  stage.advanced          — on_stage_advanced
  document.status_changed — on_document_status_changed
"""
import uuid

from sqlalchemy.orm import Session

from app.models.dependency import DependencyRule, Relationship
from app.models.workflow import WorkflowInstance, StageInstance
from app.engines import readiness as readiness_engine


def _dispatch(event_type: str, payload: dict, project_id: uuid.UUID | None, db: Session) -> None:
    """Optional webhook dispatch — silently no-ops if project_id is missing or dispatch fails."""
    if not project_id:
        return
    try:
        from app.engines.webhook_dispatcher import dispatch_event
        dispatch_event(event_type, payload, project_id, db)
    except Exception:
        pass  # Webhook dispatch must never break the main transaction


def on_task_completed(
    entity_id: uuid.UUID,
    entity_type: str,
    db: Session,
    project_id: uuid.UUID | None = None,
    task_name: str | None = None,
) -> None:
    """Task completed → re-evaluate the entity that owns the workflow."""
    readiness_engine.evaluate_entity(entity_type, entity_id, db)
    _dispatch(
        "task.completed",
        {"entity_id": str(entity_id), "entity_type": entity_type, "task_name": task_name},
        project_id,
        db,
    )


def on_stage_advanced(
    entity_id: uuid.UUID,
    entity_type: str,
    stage_key: str,
    db: Session,
    project_id: uuid.UUID | None = None,
) -> None:
    """
    Stage advanced → re-evaluate:
    1. The entity that owns the workflow.
    2. Any entities that have a dependency rule targeting this stage.
    """
    readiness_engine.evaluate_entity(entity_type, entity_id, db)
    _dispatch(
        "stage.advanced",
        {"entity_id": str(entity_id), "entity_type": entity_type, "stage_key": stage_key},
        project_id,
        db,
    )

    # Find entities with a dependency on this stage_key completing
    # (condition contains target_stage_key == stage_key)
    rules = db.query(DependencyRule).filter(
        DependencyRule.target_entity_type == entity_type,
        DependencyRule.target_entity_id == entity_id,
    ).all()

    affected: set[tuple[str, uuid.UUID]] = set()
    for rule in rules:
        if rule.source_entity_id:
            affected.add((rule.source_entity_type, rule.source_entity_id))
        else:
            # Rule applies to all entities of source type — we can't efficiently
            # enumerate all; mark for future batch evaluation. Log and skip.
            pass

    for etype, eid in affected:
        readiness_engine.evaluate_entity(etype, eid, db)


def on_deliverable_status_changed(deliverable_id: uuid.UUID, db: Session) -> None:
    """
    Deliverable status changed → re-evaluate readiness of the entity the task belongs to.
    FR-4.3.6: Deliverable approval state feeds into readiness calculation.
    """
    from app.models.deliverable import Deliverable
    from app.models.workflow import TaskInstance, StageInstance, WorkflowInstance

    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id).first()
    if not deliverable or not deliverable.task_instance_id:
        return

    task = db.query(TaskInstance).filter(TaskInstance.id == deliverable.task_instance_id).first()
    if not task:
        return

    stage = db.query(StageInstance).filter(StageInstance.id == task.stage_instance_id).first()
    if not stage:
        return

    instance = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == stage.workflow_instance_id
    ).first()
    if not instance:
        return

    readiness_engine.evaluate_entity(instance.entity_type, instance.entity_id, db)


def on_document_status_changed(
    document_id: uuid.UUID,
    db: Session,
    project_id: uuid.UUID | None = None,
    document_name: str | None = None,
    new_status: str | None = None,
) -> None:
    """
    Document status changed → re-evaluate all entities that have a
    mandatory relationship pointing to this document.
    """
    rels = db.query(Relationship).filter(
        Relationship.target_entity_id == document_id,
        Relationship.target_entity_type == "document",
    ).all()

    for rel in rels:
        readiness_engine.evaluate_entity(rel.source_entity_type, rel.source_entity_id, db)

    # Also re-evaluate the document itself (it may have its own readiness)
    readiness_engine.evaluate_entity("document", document_id, db)

    _dispatch(
        "document.status_changed",
        {
            "document_id": str(document_id),
            "document_name": document_name,
            "new_status": new_status,
        },
        project_id,
        db,
    )


def on_relationship_changed(
    source_entity_type: str,
    source_entity_id: uuid.UUID,
    target_entity_id: uuid.UUID,
    db: Session,
) -> None:
    """Relationship added or removed → re-evaluate both source and target."""
    readiness_engine.evaluate_entity(source_entity_type, source_entity_id, db)
    # Re-evaluate target too — it may be blocking something else now
    _try_evaluate_by_id(target_entity_id, db)


def on_dependency_rule_changed(rule: DependencyRule, db: Session) -> None:
    """
    Dependency rule added or deleted → re-evaluate all entities affected.
    Invariant #4: this must always be called on rule deletion.
    """
    if rule.source_entity_id:
        # Rule applies to one specific entity
        readiness_engine.evaluate_entity(rule.source_entity_type, rule.source_entity_id, db)
    else:
        # Rule applies to all entities of this source type — re-evaluate all
        # instances of that type that have an active workflow
        instances = db.query(WorkflowInstance).filter(
            WorkflowInstance.entity_type == rule.source_entity_type,
            WorkflowInstance.status == "active",
        ).all()
        seen: set[uuid.UUID] = set()
        for inst in instances:
            if inst.entity_id not in seen:
                seen.add(inst.entity_id)
                readiness_engine.evaluate_entity(rule.source_entity_type, inst.entity_id, db)


def on_class_definition_changed(class_id: uuid.UUID, db: Session) -> None:
    """Re-evaluate all Objects whose class_definition_id = class_id."""
    from app.models.object import Object
    objects = db.query(Object).filter(Object.class_definition_id == class_id).all()
    for obj in objects:
        readiness_engine.evaluate_entity("object", obj.id, db)


def _try_evaluate_by_id(entity_id: uuid.UUID, db: Session) -> None:
    """
    Attempt to evaluate an entity when we only have its ID (not its type).
    Checks objects first, then documents.
    """
    from app.models.object import Object
    from app.models.document import Document

    if db.query(Object).filter(Object.id == entity_id).first():
        readiness_engine.evaluate_entity("object", entity_id, db)
    elif db.query(Document).filter(Document.id == entity_id).first():
        readiness_engine.evaluate_entity("document", entity_id, db)
