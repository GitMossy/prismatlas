import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines.scenario import compute_scenario_cpm
from app.models.baseline import Baseline
from app.models.project import Project
from app.models.scenario import Scenario, ScenarioTaskOverride
from app.models.workflow import TaskInstance

projects_router = APIRouter(prefix="/projects", tags=["scenarios"])
scenarios_router = APIRouter(prefix="/scenarios", tags=["scenarios"])


# ── Pydantic schemas (inline — simple enough to not warrant a separate file) ───

class ScenarioCreate(BaseModel):
    name: str
    description: str | None = None
    source_baseline_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    source_baseline_id: uuid.UUID | None
    created_at: datetime
    created_by: uuid.UUID | None


class TaskOverrideUpdate(BaseModel):
    duration_days: int | None = None
    effort_hours: float | None = None
    start_offset_days: int | None = None


class TaskOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_id: uuid.UUID
    task_instance_id: uuid.UUID
    duration_days: int | None
    effort_hours: float | None
    start_offset_days: int | None


# ── Scenario CRUD ──────────────────────────────────────────────────────────────

@projects_router.post("/{project_id}/scenarios", response_model=ScenarioResponse, status_code=201)
def create_scenario(
    project_id: uuid.UUID,
    body: ScenarioCreate,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.source_baseline_id:
        baseline = db.query(Baseline).filter(Baseline.id == body.source_baseline_id).first()
        if not baseline:
            raise HTTPException(status_code=404, detail="Source baseline not found")

    scenario = Scenario(
        project_id=project_id,
        name=body.name,
        description=body.description,
        source_baseline_id=body.source_baseline_id,
        created_at=datetime.now(timezone.utc),
        created_by=body.created_by,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@projects_router.get("/{project_id}/scenarios", response_model=list[ScenarioResponse])
def list_scenarios(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(Scenario)
        .filter(Scenario.project_id == project_id)
        .order_by(Scenario.created_at.desc())
        .all()
    )


@scenarios_router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@scenarios_router.delete("/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    db.delete(scenario)
    db.commit()


# ── Task overrides ─────────────────────────────────────────────────────────────

@scenarios_router.put(
    "/{scenario_id}/tasks/{task_id}",
    response_model=TaskOverrideResponse,
)
def upsert_task_override(
    scenario_id: uuid.UUID,
    task_id: uuid.UUID,
    body: TaskOverrideUpdate,
    db: Session = Depends(get_db),
):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    task = db.query(TaskInstance).filter(TaskInstance.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task instance not found")

    override = db.query(ScenarioTaskOverride).filter(
        ScenarioTaskOverride.scenario_id == scenario_id,
        ScenarioTaskOverride.task_instance_id == task_id,
    ).first()

    if override is None:
        override = ScenarioTaskOverride(
            scenario_id=scenario_id,
            task_instance_id=task_id,
        )
        db.add(override)

    for field_name, value in body.model_dump(exclude_unset=True).items():
        setattr(override, field_name, value)

    db.commit()
    db.refresh(override)
    return override


# ── Compute scenario CPM (in-memory, no writes) ────────────────────────────────

@scenarios_router.get("/{scenario_id}/cpm", response_model=dict)
def get_scenario_cpm(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Compute CPM for the scenario in-memory.
    Does NOT modify any task_instance rows.
    Returns project_duration and per-task CPM data.
    """
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return compute_scenario_cpm(scenario_id, db)


# ── Compare two scenarios ──────────────────────────────────────────────────────

@scenarios_router.get("/{scenario_id}/compare/{other_id}", response_model=dict)
def compare_scenarios(
    scenario_id: uuid.UUID,
    other_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Compare two scenarios.
    Returns:
      - duration_delta: other.project_duration - this.project_duration
      - effort_delta: total effort_hours difference
      - task_deltas: per-task EF delta for tasks present in both scenarios
    """
    for sid in (scenario_id, other_id):
        s = db.query(Scenario).filter(Scenario.id == sid).first()
        if not s:
            raise HTTPException(status_code=404, detail=f"Scenario {sid} not found")

    result_a = compute_scenario_cpm(scenario_id, db)
    result_b = compute_scenario_cpm(other_id, db)

    if "error" in result_a:
        raise HTTPException(status_code=400, detail=result_a["error"])
    if "error" in result_b:
        raise HTTPException(status_code=400, detail=result_b["error"])

    dur_a = result_a.get("project_duration", 0)
    dur_b = result_b.get("project_duration", 0)

    tasks_a: dict[str, Any] = result_a.get("tasks", {})
    tasks_b: dict[str, Any] = result_b.get("tasks", {})

    effort_a = sum(
        (t.get("effort_hours") or 0.0) for t in tasks_a.values()
    )
    effort_b = sum(
        (t.get("effort_hours") or 0.0) for t in tasks_b.values()
    )

    common_tasks = set(tasks_a.keys()) & set(tasks_b.keys())
    task_deltas: dict[str, Any] = {}
    for tid in common_tasks:
        ef_delta = tasks_b[tid]["early_finish"] - tasks_a[tid]["early_finish"]
        if ef_delta != 0:
            task_deltas[tid] = {"early_finish_delta": ef_delta}

    return {
        "scenario_id": str(scenario_id),
        "other_id": str(other_id),
        "duration_delta": dur_b - dur_a,
        "effort_delta": round(effort_b - effort_a, 4),
        "task_deltas": task_deltas,
    }
