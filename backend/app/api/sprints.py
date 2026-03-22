import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sprint import Release, Sprint, TaskSprintAssignment
from app.models.workflow import TaskInstance
from app.schemas.sprint import (
    BurndownPoint,
    ReleaseCreate,
    ReleaseResponse,
    ReleaseUpdate,
    SprintCreate,
    SprintResponse,
    SprintUpdate,
    TaskAssignRequest,
    TaskAssignResponse,
)

releases_router = APIRouter(prefix="/releases", tags=["sprints"])
sprints_router = APIRouter(prefix="/sprints", tags=["sprints"])


# ── Releases ───────────────────────────────────────────────────────────────────

@releases_router.get("", response_model=list[ReleaseResponse])
def list_releases(
    project_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Release)
    if project_id:
        q = q.filter(Release.project_id == project_id)
    return q.order_by(Release.target_date.asc().nullslast()).all()


@releases_router.post("", response_model=ReleaseResponse, status_code=201)
def create_release(body: ReleaseCreate, db: Session = Depends(get_db)):
    release = Release(**body.model_dump())
    db.add(release)
    db.commit()
    db.refresh(release)
    return release


@releases_router.get("/{release_id}", response_model=ReleaseResponse)
def get_release(release_id: uuid.UUID, db: Session = Depends(get_db)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    return release


@releases_router.put("/{release_id}", response_model=ReleaseResponse)
def update_release(release_id: uuid.UUID, body: ReleaseUpdate, db: Session = Depends(get_db)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(release, field, value)
    db.commit()
    db.refresh(release)
    return release


@releases_router.delete("/{release_id}", status_code=204)
def delete_release(release_id: uuid.UUID, db: Session = Depends(get_db)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    db.delete(release)
    db.commit()


# ── Sprints ────────────────────────────────────────────────────────────────────

@sprints_router.get("", response_model=list[SprintResponse])
def list_sprints(
    project_id: uuid.UUID | None = None,
    release_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Sprint)
    if project_id:
        q = q.filter(Sprint.project_id == project_id)
    if release_id:
        q = q.filter(Sprint.release_id == release_id)
    return q.order_by(Sprint.start_date.asc().nullslast()).all()


@sprints_router.post("", response_model=SprintResponse, status_code=201)
def create_sprint(body: SprintCreate, db: Session = Depends(get_db)):
    sprint = Sprint(**body.model_dump())
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


@sprints_router.get("/{sprint_id}", response_model=SprintResponse)
def get_sprint(sprint_id: uuid.UUID, db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return sprint


@sprints_router.put("/{sprint_id}", response_model=SprintResponse)
def update_sprint(sprint_id: uuid.UUID, body: SprintUpdate, db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(sprint, field, value)
    db.commit()
    db.refresh(sprint)
    return sprint


@sprints_router.delete("/{sprint_id}", status_code=204)
def delete_sprint(sprint_id: uuid.UUID, db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    db.delete(sprint)
    db.commit()


# ── Task assignment within a sprint ───────────────────────────────────────────

@sprints_router.post("/{sprint_id}/tasks", response_model=TaskAssignResponse, status_code=201)
def assign_task_to_sprint(
    sprint_id: uuid.UUID,
    body: TaskAssignRequest,
    db: Session = Depends(get_db),
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    task = db.query(TaskInstance).filter(TaskInstance.id == body.task_instance_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task instance not found")

    # Prevent duplicate assignment
    existing = db.query(TaskSprintAssignment).filter(
        TaskSprintAssignment.sprint_id == sprint_id,
        TaskSprintAssignment.task_instance_id == body.task_instance_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Task already assigned to this sprint")

    assignment = TaskSprintAssignment(
        task_instance_id=body.task_instance_id,
        sprint_id=sprint_id,
        assigned_hours=body.assigned_hours,
        created_at=datetime.now(timezone.utc),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@sprints_router.delete("/{sprint_id}/tasks/{task_id}", status_code=204)
def remove_task_from_sprint(
    sprint_id: uuid.UUID,
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    assignment = db.query(TaskSprintAssignment).filter(
        TaskSprintAssignment.sprint_id == sprint_id,
        TaskSprintAssignment.task_instance_id == task_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Task assignment not found")
    db.delete(assignment)
    db.commit()


# ── Burndown chart ─────────────────────────────────────────────────────────────

@sprints_router.get("/{sprint_id}/burndown", response_model=list[BurndownPoint])
def get_burndown(sprint_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Returns a daily burndown series for the sprint.

    planned_remaining: total assigned hours not yet due by end-of-day (linear ideal burndown).
    actual_remaining:  total assigned hours for tasks NOT yet complete by end-of-day.

    If start_date or end_date is not set, returns an empty list.
    """
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    if not sprint.start_date or not sprint.end_date:
        return []

    assignments = (
        db.query(TaskSprintAssignment)
        .filter(TaskSprintAssignment.sprint_id == sprint_id)
        .all()
    )

    if not assignments:
        return []

    # Build a lookup: task_instance_id → (assigned_hours, completed_at)
    total_hours = sum((a.assigned_hours or 0.0) for a in assignments)
    if total_hours == 0.0:
        return []

    sprint_days = (sprint.end_date - sprint.start_date).days + 1
    hours_per_day = total_hours / sprint_days

    # Gather completed_at per task
    task_ids = [a.task_instance_id for a in assignments]
    tasks = db.query(TaskInstance).filter(TaskInstance.id.in_(task_ids)).all()
    task_map = {t.id: t for t in tasks}

    result: list[BurndownPoint] = []
    current = sprint.start_date
    actual_remaining = total_hours

    for day_idx in range(sprint_days):
        day = sprint.start_date + timedelta(days=day_idx)
        planned_remaining = max(0.0, total_hours - hours_per_day * (day_idx + 1))

        # Deduct hours for tasks completed on or before this day
        for a in assignments:
            task = task_map.get(a.task_instance_id)
            if (
                task
                and task.status == "complete"
                and task.completed_at
                and task.completed_at.date() == day
            ):
                actual_remaining = max(0.0, actual_remaining - (a.assigned_hours or 0.0))

        result.append(BurndownPoint(
            date=day,
            planned_remaining=round(planned_remaining, 2),
            actual_remaining=round(actual_remaining, 2),
        ))

    return result
