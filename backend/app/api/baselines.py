import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines.ev import compute_ev
from app.models.baseline import Baseline, BaselineTask
from app.models.project import Project
from app.models.workflow import TaskInstance, StageInstance, WorkflowInstance
from app.schemas.baseline import BaselineCreate, BaselineResponse, EVResponse

projects_router = APIRouter(prefix="/projects", tags=["baselines"])
baselines_router = APIRouter(prefix="/baselines", tags=["baselines"])


# ── Create baseline (snapshot current CPM state) ───────────────────────────────

@projects_router.post("/{project_id}/baselines", response_model=BaselineResponse, status_code=201)
def create_baseline(
    project_id: uuid.UUID,
    body: BaselineCreate,
    db: Session = Depends(get_db),
):
    """
    Snapshot the current CPM schedule for all active workflow instances
    in this project into an immutable baseline.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    baseline = Baseline(
        project_id=project_id,
        name=body.name,
        description=body.description,
        created_at=datetime.now(timezone.utc),
        created_by=body.created_by,
    )
    db.add(baseline)
    db.flush()

    # Collect all task instances from active workflow instances in this project
    # that have CPM data (early_start/early_finish populated)
    active_instances = (
        db.query(WorkflowInstance)
        .filter(WorkflowInstance.status == "active")
        .join(StageInstance, StageInstance.workflow_instance_id == WorkflowInstance.id)
        .join(TaskInstance, TaskInstance.stage_instance_id == StageInstance.id)
        .all()
    )

    # Deduplicate instance ids
    seen_instance_ids: set[uuid.UUID] = set()
    all_tasks: list[TaskInstance] = []

    for wi in active_instances:
        if wi.id in seen_instance_ids:
            continue
        seen_instance_ids.add(wi.id)
        for stage in wi.stage_instances:
            for task in stage.task_instances:
                all_tasks.append(task)

    for task in all_tasks:
        bt = BaselineTask(
            baseline_id=baseline.id,
            task_instance_id=task.id,
            planned_start=task.early_start,
            planned_finish=task.early_finish,
            planned_effort_hours=task.effort_hours,
            planned_cost=None,
            early_start=task.early_start,
            early_finish=task.early_finish,
            late_start=task.late_start,
            late_finish=task.late_finish,
            total_float=task.total_float,
        )
        db.add(bt)

    db.commit()
    db.refresh(baseline)
    return baseline


# ── List baselines for a project ───────────────────────────────────────────────

@projects_router.get("/{project_id}/baselines", response_model=list[BaselineResponse])
def list_baselines(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(Baseline)
        .filter(Baseline.project_id == project_id)
        .order_by(Baseline.created_at.desc())
        .all()
    )


# ── Get single baseline ────────────────────────────────────────────────────────

@baselines_router.get("/{baseline_id}", response_model=BaselineResponse)
def get_baseline(baseline_id: uuid.UUID, db: Session = Depends(get_db)):
    baseline = db.query(Baseline).filter(Baseline.id == baseline_id).first()
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return baseline


# ── Earned Value ──────────────────────────────────────────────────────────────

@baselines_router.get("/{baseline_id}/ev", response_model=EVResponse)
def get_ev(
    baseline_id: uuid.UUID,
    as_of: int = Query(..., description="Day offset from project start"),
    db: Session = Depends(get_db),
):
    """
    Compute Earned Value metrics for a baseline as of the given day offset.
    PV = planned value (sum of planned hours due by as_of)
    EV = earned value (planned hours for completed tasks due by as_of)
    SPI = EV / PV
    """
    baseline = db.query(Baseline).filter(Baseline.id == baseline_id).first()
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")

    result = compute_ev(baseline_id, as_of, db)
    return result
