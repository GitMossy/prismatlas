import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.engines import triggers
from app.engines.type_propagation import propagate_template_change
from app.models.workflow import (
    WorkflowTemplate,
    WorkflowTemplateVersion,
    WorkflowInstance,
    StageInstance,
    TaskInstance,
)
from app.schemas.workflow import (
    WorkflowTemplateCreate,
    WorkflowTemplateUpdate,
    WorkflowTemplateResponse,
    WorkflowTemplateVersionCreate,
    WorkflowTemplateVersionResponse,
    WorkflowInstantiateRequest,
    WorkflowInstanceResponse,
    TaskCompleteRequest,
    StageAdvanceResponse,
)

templates_router = APIRouter(prefix="/workflow-templates", tags=["workflow-templates"])
entities_router = APIRouter(prefix="/entities", tags=["workflow-instances"])


# --- Workflow Templates ---

@templates_router.get("", response_model=list[WorkflowTemplateResponse])
def list_templates(db: Session = Depends(get_db)):
    return db.query(WorkflowTemplate).all()


@templates_router.post("", response_model=WorkflowTemplateResponse, status_code=201)
def create_template(body: WorkflowTemplateCreate, db: Session = Depends(get_db)):
    template = WorkflowTemplate(**body.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@templates_router.get("/{template_id}", response_model=WorkflowTemplateResponse)
def get_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return template


@templates_router.put("/{template_id}", response_model=WorkflowTemplateResponse)
def update_template(template_id: uuid.UUID, body: WorkflowTemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@templates_router.delete("/{template_id}", status_code=204)
def delete_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    # Protect against deleting if active workflow instances reference versions of this template
    active_instance = (
        db.query(WorkflowInstance)
        .join(WorkflowTemplateVersion, WorkflowInstance.template_version_id == WorkflowTemplateVersion.id)
        .filter(
            WorkflowTemplateVersion.template_id == template_id,
            WorkflowInstance.status == "active",
        )
        .first()
    )
    if active_instance:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete template: active workflow instances are using it",
        )
    db.delete(template)
    db.commit()


@templates_router.post("/{template_id}/versions", response_model=WorkflowTemplateVersionResponse, status_code=201)
def create_template_version(
    template_id: uuid.UUID,
    body: WorkflowTemplateVersionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    latest = (
        db.query(WorkflowTemplateVersion)
        .filter(WorkflowTemplateVersion.template_id == template_id)
        .order_by(WorkflowTemplateVersion.version_number.desc())
        .first()
    )
    next_version = (latest.version_number + 1) if latest else 1

    version = WorkflowTemplateVersion(
        template_id=template_id,
        version_number=next_version,
        definition=body.definition,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    # FR-4.2.5: If this is a root/parent template (no parent itself), propagate
    # changes to all child templates and their live instances in the background.
    if template.parent_template_id is None:
        background_tasks.add_task(propagate_template_change, version.id, db)

    return version


@templates_router.get("/{template_id}/children", response_model=list[WorkflowTemplateResponse])
def get_template_children(template_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return all templates that inherit from this template (direct children only)."""
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return (
        db.query(WorkflowTemplate)
        .filter(WorkflowTemplate.parent_template_id == template_id)
        .all()
    )


@templates_router.post("/{template_id}/propagate", response_model=dict)
def manual_propagate(template_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Manually trigger propagation of the template's latest active version
    to all child templates and their live instances.
    """
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    active_version = (
        db.query(WorkflowTemplateVersion)
        .filter(
            WorkflowTemplateVersion.template_id == template_id,
            WorkflowTemplateVersion.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not active_version:
        raise HTTPException(status_code=404, detail="No active version found for this template")

    count = propagate_template_change(active_version.id, db)
    return {"instances_updated": count, "template_version_id": str(active_version.id)}


@templates_router.get("/{template_id}/versions", response_model=list[WorkflowTemplateVersionResponse])
def list_template_versions(template_id: uuid.UUID, db: Session = Depends(get_db)):
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return (
        db.query(WorkflowTemplateVersion)
        .filter(WorkflowTemplateVersion.template_id == template_id)
        .order_by(WorkflowTemplateVersion.version_number.desc())
        .all()
    )


@templates_router.get("/{template_id}/versions/{version_number}", response_model=WorkflowTemplateVersionResponse)
def get_template_version(
    template_id: uuid.UUID,
    version_number: int,
    db: Session = Depends(get_db),
):
    version = (
        db.query(WorkflowTemplateVersion)
        .filter(
            WorkflowTemplateVersion.template_id == template_id,
            WorkflowTemplateVersion.version_number == version_number,
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Template version not found")
    return version


@templates_router.delete("/{template_id}/versions/{version_number}", status_code=204)
def delete_template_version(
    template_id: uuid.UUID,
    version_number: int,
    db: Session = Depends(get_db),
):
    version = (
        db.query(WorkflowTemplateVersion)
        .filter(
            WorkflowTemplateVersion.template_id == template_id,
            WorkflowTemplateVersion.version_number == version_number,
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Template version not found")
    active_instance = (
        db.query(WorkflowInstance)
        .filter(WorkflowInstance.template_version_id == version.id, WorkflowInstance.status == "active")
        .first()
    )
    if active_instance:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete version: active workflow instances are using it",
        )
    db.delete(version)
    db.commit()


@templates_router.patch("/{template_id}/versions/{version_number}/activate", response_model=WorkflowTemplateVersionResponse)
def activate_template_version(
    template_id: uuid.UUID,
    version_number: int,
    db: Session = Depends(get_db),
):
    versions = (
        db.query(WorkflowTemplateVersion)
        .filter(WorkflowTemplateVersion.template_id == template_id)
        .all()
    )
    target = next((v for v in versions if v.version_number == version_number), None)
    if not target:
        raise HTTPException(status_code=404, detail="Template version not found")
    for v in versions:
        v.is_active = v.version_number == version_number
    db.commit()
    db.refresh(target)
    return target


# --- Workflow Instances ---

def _load_instance(entity_id: uuid.UUID, db: Session) -> WorkflowInstance:
    instance = (
        db.query(WorkflowInstance)
        .options(
            joinedload(WorkflowInstance.stage_instances).joinedload(StageInstance.task_instances)
        )
        .filter(WorkflowInstance.entity_id == entity_id, WorkflowInstance.status == "active")
        .first()
    )
    if not instance:
        raise HTTPException(status_code=404, detail="No active workflow found for this entity")
    return instance


@entities_router.post("/{entity_id}/workflow", response_model=WorkflowInstanceResponse, status_code=201)
def instantiate_workflow(
    entity_id: uuid.UUID,
    body: WorkflowInstantiateRequest,
    entity_type: str,  # query param: "object" or "document"
    db: Session = Depends(get_db),
):
    version = db.query(WorkflowTemplateVersion).filter(
        WorkflowTemplateVersion.id == body.template_version_id
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Template version not found")

    # Prevent duplicate active workflow
    existing = db.query(WorkflowInstance).filter(
        WorkflowInstance.entity_id == entity_id,
        WorkflowInstance.status == "active",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Entity already has an active workflow")

    instance = WorkflowInstance(
        entity_type=entity_type,
        entity_id=entity_id,
        template_version_id=version.id,
        status="active",
    )
    db.add(instance)
    db.flush()

    stages = sorted(version.definition.get("stages", []), key=lambda s: s["order"])
    for i, stage_def in enumerate(stages):
        stage = StageInstance(
            workflow_instance_id=instance.id,
            stage_key=stage_def["key"],
            stage_name=stage_def["name"],
            stage_order=stage_def["order"],
            status="active" if i == 0 else "pending",
            started_at=datetime.now(timezone.utc) if i == 0 else None,
        )
        db.add(stage)
        db.flush()

        for task_def in sorted(stage_def.get("tasks", []), key=lambda t: t["order"]):
            task = TaskInstance(
                stage_instance_id=stage.id,
                task_key=task_def["key"],
                task_name=task_def["name"],
                task_order=task_def["order"],
                is_mandatory=task_def.get("is_mandatory", True),
                status="pending",
            )
            db.add(task)

    db.commit()
    return _load_instance(entity_id, db)


@entities_router.get("/{entity_id}/workflow", response_model=WorkflowInstanceResponse)
def get_workflow(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    return _load_instance(entity_id, db)


@entities_router.put("/{entity_id}/workflow/stages/{stage_id}/advance", response_model=StageAdvanceResponse)
def advance_stage(entity_id: uuid.UUID, stage_id: uuid.UUID, db: Session = Depends(get_db)):
    instance = _load_instance(entity_id, db)

    stage = next((s for s in instance.stage_instances if s.id == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found on this workflow")
    if stage.status != "active":
        raise HTTPException(status_code=400, detail=f"Stage is '{stage.status}', not 'active'")

    # Exit criteria: all mandatory tasks must be complete
    incomplete = [t for t in stage.task_instances if t.is_mandatory and t.status != "complete"]
    if incomplete:
        names = ", ".join(t.task_name for t in incomplete)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot advance: mandatory tasks not complete: {names}",
        )

    now = datetime.now(timezone.utc)
    stage.status = "complete"
    stage.completed_at = now

    # Activate next stage
    next_stage = next(
        (s for s in instance.stage_instances if s.stage_order == stage.stage_order + 1), None
    )
    if next_stage:
        next_stage.status = "active"
        next_stage.started_at = now
    else:
        instance.status = "completed"

    db.commit()

    triggers.on_stage_advanced(entity_id, instance.entity_type, stage.stage_key, db)

    return StageAdvanceResponse(
        message="Stage advanced successfully",
        completed_stage=stage.stage_name,
        next_stage=next_stage.stage_name if next_stage else None,
        workflow_status=instance.status,
    )


def _effort_duration_warnings(
    duration_days: float | None,
    effort_hours: float | None,
    hours_per_day: float = 8.0,
    threshold: float = 0.5,
) -> list[str]:
    """
    BR-5.3: Return warnings when effort > duration × hours_per_day by more
    than `threshold` (default 50%).  Returns [] when no warning applies.
    """
    warnings = []
    if duration_days and effort_hours:
        capacity = duration_days * hours_per_day
        if capacity > 0 and effort_hours > capacity * (1 + threshold):
            warnings.append(
                f"Effort ({effort_hours}h) exceeds duration capacity "
                f"({duration_days}d × {hours_per_day}h = {capacity}h) "
                f"by more than {int(threshold * 100)}%. Consider extending duration or reducing effort."
            )
    return warnings


@entities_router.patch("/{entity_id}/workflow/tasks/{task_id}", response_model=dict)
def update_task_scheduling(
    entity_id: uuid.UUID,
    task_id: uuid.UUID,
    duration_days: float | None = None,
    effort_hours: float | None = None,
    assigned_resource_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    """
    Update scheduling fields on a task (duration, effort, resource).
    BR-5.3: Returns warnings when effort > duration capacity threshold.
    """
    instance = _load_instance(entity_id, db)
    task = None
    for stage in instance.stage_instances:
        task = next((t for t in stage.task_instances if t.id == task_id), None)
        if task:
            break
    if not task:
        raise HTTPException(status_code=404, detail="Task not found on this workflow")

    if duration_days is not None:
        if duration_days < 0.5:
            raise HTTPException(
                status_code=422,
                detail="duration_days must be at least 0.5 (half-day minimum, FR-4.3.2)",
            )
        task.duration_days = duration_days
    if effort_hours is not None:
        task.effort_hours = effort_hours
    if assigned_resource_id is not None:
        task.assigned_resource_id = assigned_resource_id

    db.commit()
    db.refresh(task)

    warnings = _effort_duration_warnings(task.duration_days, task.effort_hours)
    return {
        "message": f"Task '{task.task_name}' scheduling updated",
        "task_id": str(task_id),
        "warnings": warnings,
    }


@entities_router.post("/{entity_id}/workflow/instances/{instance_id}/reset-overrides", response_model=dict)
def reset_instance_overrides(
    entity_id: uuid.UUID,
    instance_id: uuid.UUID,
    field_keys: list[str] | None = None,
    db: Session = Depends(get_db),
):
    """
    FR-4.2.5 / Tier-2: Reset overridden fields on a WorkflowInstance back to
    the values in the current template version.  If `field_keys` is None,
    all overrides are cleared.
    """
    instance = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == instance_id,
        WorkflowInstance.entity_id == entity_id,
    ).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    if field_keys is None:
        cleared = list((instance.overridden_fields or {}).keys())
        instance.overridden_fields = {}
    else:
        overrides = dict(instance.overridden_fields or {})
        cleared = [k for k in field_keys if k in overrides]
        for k in cleared:
            del overrides[k]
        instance.overridden_fields = overrides

    db.commit()
    return {
        "message": "Overrides cleared",
        "cleared_fields": cleared,
        "remaining_overrides": list((instance.overridden_fields or {}).keys()),
    }


@entities_router.put("/{entity_id}/workflow/tasks/{task_id}/complete", response_model=dict)
def complete_task(
    entity_id: uuid.UUID,
    task_id: uuid.UUID,
    body: TaskCompleteRequest,
    db: Session = Depends(get_db),
):
    instance = _load_instance(entity_id, db)

    task = None
    for stage in instance.stage_instances:
        task = next((t for t in stage.task_instances if t.id == task_id), None)
        if task:
            if stage.status != "active":
                raise HTTPException(status_code=400, detail="Task's stage is not active")
            break

    if not task:
        raise HTTPException(status_code=404, detail="Task not found on this workflow")
    if task.status == "complete":
        raise HTTPException(status_code=400, detail="Task is already complete")

    task.status = "complete"
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by = body.completed_by
    task.notes = body.notes
    db.commit()

    triggers.on_task_completed(entity_id, instance.entity_type, db)

    return {"message": f"Task '{task.task_name}' marked complete", "task_id": str(task_id)}


# ---------------------------------------------------------------------------
# C5: Undo endpoints — reopen task / revert stage
# ---------------------------------------------------------------------------

tasks_router = APIRouter(prefix="/tasks", tags=["workflow-undo"])
stages_router = APIRouter(prefix="/stages", tags=["workflow-undo"])


@tasks_router.patch("/{task_id}/reopen", response_model=dict)
def reopen_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Set a task status back to 'pending', clearing completed_at and completed_by.
    NFR-7.2 undo support.
    """
    task = db.query(TaskInstance).filter(TaskInstance.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("complete", "in_progress"):
        raise HTTPException(status_code=400, detail=f"Task is '{task.status}', cannot reopen")
    task.status = "pending"
    task.completed_at = None
    task.completed_by = None
    db.commit()
    db.refresh(task)
    return {"message": f"Task '{task.task_name}' reopened", "task_id": str(task_id)}


@stages_router.patch("/{stage_id}/revert", response_model=dict)
def revert_stage(stage_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Set a stage status back to 'pending', clearing started_at and completed_at.
    NFR-7.2 undo support.
    """
    stage = db.query(StageInstance).filter(StageInstance.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    if stage.status not in ("complete", "active"):
        raise HTTPException(status_code=400, detail=f"Stage is '{stage.status}', cannot revert")
    stage.status = "pending"
    stage.started_at = None
    stage.completed_at = None
    db.commit()
    db.refresh(stage)
    return {"message": f"Stage '{stage.stage_name}' reverted to pending", "stage_id": str(stage_id)}
