"""
Schedule API — FR-4.4.2, FR-4.4.4

Endpoints:
  POST /workflow-instances/{instance_id}/schedule/run
      Triggers CPM forward/backward pass and persists dates.

  GET  /workflow-instances/{instance_id}/schedule
      Returns the CPM schedule as a list of task rows with dates and float.

  PUT  /workflow-instances/{instance_id}/tasks/{task_id}/duration
      Update duration_days / effort_hours on a specific TaskInstance, then
      re-run CPM.

  GET  /workflow-instances/{instance_id}/resource-loading
      Per-resource, per-day load data (FR-4.4.4).

  POST /workflow-instances/{instance_id}/schedule/level
      Propose a resource-leveled schedule (FR-4.4.4). Does NOT persist.
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines.cpm import run_cpm, get_critical_path
from app.engines.resource_leveling import compute_resource_loading, level_resources
from app.models.workflow import WorkflowInstance, TaskInstance

router = APIRouter(prefix="/workflow-instances", tags=["schedule"])


class TaskScheduleRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: uuid.UUID
    task_key: str
    task_name: str
    stage_key: str
    stage_name: str
    duration_days: int | None
    effort_hours: float | None
    assigned_resource_id: uuid.UUID | None
    early_start: int | None
    early_finish: int | None
    late_start: int | None
    late_finish: int | None
    total_float: int | None
    is_critical: bool
    is_near_critical: bool


class ScheduleResponse(BaseModel):
    workflow_instance_id: uuid.UUID
    project_duration_days: int
    critical_path_task_ids: list[uuid.UUID]
    tasks: list[TaskScheduleRow]


class TaskDurationUpdate(BaseModel):
    duration_days: int | None = None
    effort_hours: float | None = None
    assigned_resource_id: uuid.UUID | None = None


@router.post("/{instance_id}/schedule/run", response_model=ScheduleResponse)
def run_schedule(
    instance_id: uuid.UUID,
    near_critical_threshold: int = 5,
    db: Session = Depends(get_db),
):
    """Trigger CPM calculation and persist dates for all tasks in this workflow instance."""
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    nodes = run_cpm(instance_id, db, near_critical_threshold_days=near_critical_threshold)
    if not nodes:
        raise HTTPException(status_code=422, detail="No tasks found in this workflow instance")

    critical_ids = get_critical_path(nodes)
    project_duration = max(n.early_finish for n in nodes.values()) if nodes else 0

    return _build_schedule_response(instance_id, project_duration, critical_ids, db)


@router.get("/{instance_id}/schedule", response_model=ScheduleResponse)
def get_schedule(instance_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return the last-computed CPM schedule without recalculating."""
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    # Gather all tasks
    all_tasks: list[TaskInstance] = []
    for stage in instance.stage_instances:
        all_tasks.extend(stage.task_instances)

    if not all_tasks:
        raise HTTPException(status_code=422, detail="No tasks in this workflow instance")

    critical_ids = [t.id for t in all_tasks if t.is_critical]
    project_duration = max((t.early_finish or 0) for t in all_tasks)

    return _build_schedule_response(instance_id, project_duration, critical_ids, db)


@router.put("/{instance_id}/tasks/{task_id}/duration", response_model=ScheduleResponse)
def update_task_duration(
    instance_id: uuid.UUID,
    task_id: uuid.UUID,
    body: TaskDurationUpdate,
    db: Session = Depends(get_db),
):
    """Update duration/effort for a task, then re-run CPM."""
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    task = db.query(TaskInstance).filter(TaskInstance.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task instance not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()

    nodes = run_cpm(instance_id, db)
    critical_ids = get_critical_path(nodes)
    project_duration = max(n.early_finish for n in nodes.values()) if nodes else 0

    return _build_schedule_response(instance_id, project_duration, critical_ids, db)


def _build_schedule_response(
    instance_id: uuid.UUID,
    project_duration: int,
    critical_ids: list[uuid.UUID],
    db: Session,
) -> ScheduleResponse:
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    rows: list[TaskScheduleRow] = []
    for stage in sorted(instance.stage_instances, key=lambda s: s.stage_order):
        for task in sorted(stage.task_instances, key=lambda t: t.task_order):
            rows.append(TaskScheduleRow(
                task_id=task.id,
                task_key=task.task_key,
                task_name=task.task_name,
                stage_key=stage.stage_key,
                stage_name=stage.stage_name,
                duration_days=task.duration_days,
                effort_hours=task.effort_hours,
                assigned_resource_id=task.assigned_resource_id,
                early_start=task.early_start,
                early_finish=task.early_finish,
                late_start=task.late_start,
                late_finish=task.late_finish,
                total_float=task.total_float,
                is_critical=task.is_critical,
                is_near_critical=task.is_near_critical,
            ))
    return ScheduleResponse(
        workflow_instance_id=instance_id,
        project_duration_days=project_duration,
        critical_path_task_ids=critical_ids,
        tasks=rows,
    )


# ── FR-4.4.4: Resource loading and leveling ───────────────────────────────────

@router.get("/{instance_id}/resource-loading")
def get_resource_loading(
    instance_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Return per-resource, per-day loading data for this workflow instance.
    CPM must have been run first (early_start must be populated).
    Response: [{resource_id, resource_name, day, effort_hours, capacity_hours, utilization_pct}]
    """
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    return compute_resource_loading(instance_id, db)


@router.post("/{instance_id}/schedule/level")
def propose_leveled_schedule(
    instance_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Propose a resource-leveled schedule using list-scheduling heuristic.
    Does NOT persist changes — returns proposed task shifts for user review.
    Call POST /schedule/run after confirming to persist the leveled dates.

    Response:
      {
        "leveled_tasks": [{task_id, task_name, original_start, proposed_start, shift_days, leveled}],
        "over_allocated_resolved": int,
        "over_allocated_remaining": int
      }
    """
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    return level_resources(instance_id, db)
