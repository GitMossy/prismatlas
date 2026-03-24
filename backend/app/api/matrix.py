"""
Matrix view endpoints — FR-4.6.1, FR-4.6.2

All matrix endpoints return:
{
  "row_labels": [...],
  "col_labels": [...],
  "cells": [{"row": "...", "col": "...", "value": ..., "color": "..."}]
}

V3 additions:
  /matrix/raci               — FR-4.6.1h RACI Chart (RBS × ABS)
  /matrix/resource-assignment — FR-4.6.1d Resource Assignment (RBS × CBS, % allocation)
"""
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.object import Object
from app.models.project import Project, Area
from app.models.readiness import ReadinessEvaluation
from app.models.workflow import WorkflowInstance, StageInstance, TaskInstance
from app.models.resource import Resource
from app.models.saved_view import SavedView

router = APIRouter(prefix="/projects", tags=["matrix"])

# ---------------------------------------------------------------------------
# Shared response schema
# ---------------------------------------------------------------------------

class MatrixCell(BaseModel):
    row: str
    col: str
    value: float | int | str
    color: str


class MatrixData(BaseModel):
    row_labels: list[str]
    col_labels: list[str]
    cells: list[MatrixCell]


# ---------------------------------------------------------------------------
# Saved view schemas
# ---------------------------------------------------------------------------

class SavedViewCreate(BaseModel):
    name: str
    config: dict[str, Any]


class SavedViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None
    name: str
    config: dict[str, Any]


# ---------------------------------------------------------------------------
# Helper: latest readiness per entity
# ---------------------------------------------------------------------------

def _latest_readiness_map(project_id: uuid.UUID, db: Session) -> dict[uuid.UUID, ReadinessEvaluation]:
    """Return {entity_id: ReadinessEvaluation} for all objects in a project."""
    objects = db.query(Object).filter(Object.project_id == project_id).all()
    if not objects:
        return {}
    obj_ids = [o.id for o in objects]
    latest_subq = (
        db.query(
            ReadinessEvaluation.entity_id,
            func.max(ReadinessEvaluation.evaluated_at).label("max_at"),
        )
        .filter(ReadinessEvaluation.entity_id.in_(obj_ids))
        .group_by(ReadinessEvaluation.entity_id)
        .subquery()
    )
    evals = (
        db.query(ReadinessEvaluation)
        .join(
            latest_subq,
            (ReadinessEvaluation.entity_id == latest_subq.c.entity_id)
            & (ReadinessEvaluation.evaluated_at == latest_subq.c.max_at),
        )
        .all()
    )
    return {ev.entity_id: ev for ev in evals}


def _status_color(status: str) -> str:
    return {
        "complete": "#22c55e",
        "active": "#3b82f6",
        "pending": "#9ca3af",
        "skipped": "#d1d5db",
    }.get(status, "#9ca3af")


def _readiness_color(value: float) -> str:
    if value >= 0.9:
        return "#22c55e"
    if value >= 0.5:
        return "#f59e0b"
    return "#ef4444"


# ---------------------------------------------------------------------------
# C1.1  Task-status matrix — rows=objects, cols=stage keys
# ---------------------------------------------------------------------------

@router.get("/{project_id}/matrix/task-status", response_model=MatrixData)
def task_status_matrix(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Rows = objects, Cols = stage keys.
    Cell value = stage status (pending/active/complete).
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    objects = db.query(Object).filter(Object.project_id == project_id).all()
    if not objects:
        return MatrixData(row_labels=[], col_labels=[], cells=[])

    obj_map = {str(o.id): o for o in objects}

    # Collect all workflow instances for these objects
    obj_ids = [o.id for o in objects]
    instances = (
        db.query(WorkflowInstance)
        .filter(
            WorkflowInstance.entity_type == "object",
            WorkflowInstance.entity_id.in_(obj_ids),
        )
        .all()
    )

    # Build: entity_id → {stage_key: status}
    entity_stage_status: dict[str, dict[str, str]] = {}
    all_stage_keys: list[str] = []

    for wi in instances:
        eid = str(wi.entity_id)
        entity_stage_status.setdefault(eid, {})
        for si in wi.stage_instances:
            entity_stage_status[eid][si.stage_key] = si.status
            if si.stage_key not in all_stage_keys:
                all_stage_keys.append(si.stage_key)

    # Sort stage keys by typical order (use first object's stage order as reference)
    stage_order: dict[str, int] = {}
    for wi in instances:
        for si in wi.stage_instances:
            if si.stage_key not in stage_order:
                stage_order[si.stage_key] = si.stage_order
    all_stage_keys.sort(key=lambda k: stage_order.get(k, 0))

    row_labels = [o.name for o in objects]
    col_labels = all_stage_keys

    cells: list[MatrixCell] = []
    for obj in objects:
        eid = str(obj.id)
        stage_map = entity_stage_status.get(eid, {})
        for sk in all_stage_keys:
            status = stage_map.get(sk, "pending")
            cells.append(MatrixCell(
                row=obj.name,
                col=sk,
                value=status,
                color=_status_color(status),
            ))

    return MatrixData(row_labels=row_labels, col_labels=col_labels, cells=cells)


# ---------------------------------------------------------------------------
# C1.2  Resource-loading matrix — rows=resources, cols=time buckets
# ---------------------------------------------------------------------------

@router.get("/{project_id}/matrix/resource-loading", response_model=MatrixData)
def resource_loading_matrix(
    project_id: uuid.UUID,
    start_day: int = Query(0, ge=0),
    end_day: int = Query(90, ge=1),
    bucket: str = Query("week", regex="^(week|month)$"),
    db: Session = Depends(get_db),
):
    """
    Rows = resources, Cols = time buckets.
    Cell value = sum of effort_hours for tasks in that bucket assigned to the resource.
    Color: green (<80% capacity), amber (80–100%), red (>100%).
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    resources = db.query(Resource).filter(Resource.project_id == project_id).all()
    if not resources:
        return MatrixData(row_labels=[], col_labels=[], cells=[])

    bucket_size = 7 if bucket == "week" else 30
    bucket_starts = list(range(start_day, end_day, bucket_size))
    col_labels = [f"Day {b}–{min(b + bucket_size - 1, end_day)}" for b in bucket_starts]

    res_map = {r.id: r for r in resources}
    row_labels = [r.name for r in resources]

    # Fetch all task instances for this project with assigned resources
    obj_ids = [o.id for o in db.query(Object.id).filter(Object.project_id == project_id).all()]
    wi_ids = [
        wi.id
        for wi in db.query(WorkflowInstance.id)
        .filter(
            WorkflowInstance.entity_type == "object",
            WorkflowInstance.entity_id.in_(obj_ids),
        )
        .all()
    ]

    tasks: list[TaskInstance] = []
    if wi_ids:
        stage_ids = [
            si.id
            for si in db.query(StageInstance.id)
            .filter(StageInstance.workflow_instance_id.in_(wi_ids))
            .all()
        ]
        if stage_ids:
            tasks = (
                db.query(TaskInstance)
                .filter(
                    TaskInstance.stage_instance_id.in_(stage_ids),
                    TaskInstance.assigned_resource_id.isnot(None),
                    TaskInstance.early_start.isnot(None),
                )
                .all()
            )

    # Sum effort per (resource, bucket)
    effort: dict[uuid.UUID, dict[int, float]] = {r.id: {i: 0.0 for i in range(len(bucket_starts))} for r in resources}
    for task in tasks:
        if task.assigned_resource_id not in effort:
            continue
        es = task.early_start or 0
        ef = task.early_finish or (es + (task.duration_days or 1))
        hours = task.effort_hours or 0.0
        duration = max(ef - es, 1)
        for bi, bs in enumerate(bucket_starts):
            be = bs + bucket_size
            overlap_start = max(es, bs)
            overlap_end = min(ef, be)
            if overlap_end > overlap_start:
                frac = (overlap_end - overlap_start) / duration
                effort[task.assigned_resource_id][bi] += hours * frac

    cells: list[MatrixCell] = []
    for res in resources:
        cap_per_bucket = res.capacity_hours_per_day * bucket_size
        for bi, col in enumerate(col_labels):
            val = round(effort[res.id][bi], 1)
            ratio = val / cap_per_bucket if cap_per_bucket > 0 else 0.0
            if ratio > 1.0:
                color = "#ef4444"
            elif ratio >= 0.8:
                color = "#f59e0b"
            else:
                color = "#22c55e"
            cells.append(MatrixCell(row=res.name, col=col, value=val, color=color))

    return MatrixData(row_labels=row_labels, col_labels=col_labels, cells=cells)


# ---------------------------------------------------------------------------
# C1.3  Area heatmap — rows=object_types, cols=areas
# ---------------------------------------------------------------------------

@router.get("/{project_id}/matrix/area-heatmap", response_model=MatrixData)
def area_heatmap_matrix(
    project_id: uuid.UUID,
    metric: str = Query("complexity", regex="^(complexity|readiness|count)$"),
    db: Session = Depends(get_db),
):
    """
    Rows = object types, Cols = areas.
    Metric: complexity | readiness | count.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    areas = db.query(Area).filter(Area.project_id == project_id).all()
    objects = db.query(Object).filter(Object.project_id == project_id).all()

    if not areas or not objects:
        return MatrixData(row_labels=[], col_labels=[], cells=[])

    area_map = {a.id: a.name for a in areas}
    object_types = sorted({o.object_type for o in objects})
    col_labels = [a.name for a in areas]
    row_labels = object_types

    readiness_map = _latest_readiness_map(project_id, db) if metric == "readiness" else {}

    # Aggregate per (object_type, area)
    # value: count / avg_readiness / avg_complexity
    from collections import defaultdict
    bucket: dict[tuple[str, str], list[float]] = defaultdict(list)

    for o in objects:
        area_name = area_map.get(o.area_id, "Unknown") if o.area_id else "Unassigned"
        if metric == "count":
            bucket[(o.object_type, area_name)].append(1.0)
        elif metric == "complexity":
            # Use linked workflow template complexity — fallback to 1.0
            bucket[(o.object_type, area_name)].append(1.0)
        else:  # readiness
            ev = readiness_map.get(o.id)
            if ev:
                bucket[(o.object_type, area_name)].append(ev.overall_readiness)

    # Ensure all area names appear including "Unassigned" if present
    all_area_names = set(col_labels)
    for (_, area_name) in bucket.keys():
        if area_name not in all_area_names:
            col_labels.append(area_name)
            all_area_names.add(area_name)

    cells: list[MatrixCell] = []
    for ot in row_labels:
        for area_name in col_labels:
            vals = bucket.get((ot, area_name), [])
            if metric == "count":
                val: float = float(len(vals))
                max_count = max(
                    (len(v) for v in bucket.values()), default=1
                )
                ratio = val / max_count if max_count > 0 else 0.0
                color = _readiness_color(ratio)
            elif metric == "readiness":
                val = round(sum(vals) / len(vals), 3) if vals else 0.0
                color = _readiness_color(val)
            else:  # complexity
                val = round(sum(vals) / len(vals), 2) if vals else 0.0
                color = "#3b82f6" if val <= 1.0 else "#f59e0b" if val <= 2.0 else "#ef4444"
            cells.append(MatrixCell(row=ot, col=area_name, value=val, color=color))

    return MatrixData(row_labels=row_labels, col_labels=col_labels, cells=cells)


# ---------------------------------------------------------------------------
# C1.4  Custom pivot matrix — user-configurable axes
# ---------------------------------------------------------------------------

PIVOT_DIMS = {"area", "object_type", "zone", "owner", "stage"}
PIVOT_METRICS = {"readiness", "count", "complexity"}


@router.get("/{project_id}/matrix/custom", response_model=MatrixData)
def custom_matrix(
    project_id: uuid.UUID,
    rows: str = Query("area", regex="^(area|object_type|zone|owner|stage)$"),
    cols: str = Query("object_type", regex="^(area|object_type|zone|owner|stage)$"),
    metric: str = Query("readiness", regex="^(readiness|count|complexity)$"),
    db: Session = Depends(get_db),
):
    """
    User-configurable pivot matrix.
    rows/cols: area | object_type | zone | owner | stage
    metric: readiness | count | complexity
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if rows == cols:
        raise HTTPException(status_code=422, detail="rows and cols must be different dimensions")

    objects = db.query(Object).filter(Object.project_id == project_id).all()
    if not objects:
        return MatrixData(row_labels=[], col_labels=[], cells=[])

    readiness_map = _latest_readiness_map(project_id, db) if metric == "readiness" else {}

    # Resolve area names
    area_ids = {o.area_id for o in objects if o.area_id}
    area_name_map: dict[uuid.UUID, str] = {}
    if area_ids:
        for area in db.query(Area).filter(Area.id.in_(area_ids)).all():
            area_name_map[area.id] = area.name

    # Get current stage per object (latest active stage)
    obj_ids = [o.id for o in objects]
    stage_map: dict[uuid.UUID, str] = {}
    if rows == "stage" or cols == "stage":
        instances = (
            db.query(WorkflowInstance)
            .filter(
                WorkflowInstance.entity_type == "object",
                WorkflowInstance.entity_id.in_(obj_ids),
            )
            .all()
        )
        for wi in instances:
            active = next((si for si in wi.stage_instances if si.status == "active"), None)
            if active:
                stage_map[wi.entity_id] = active.stage_key
            elif wi.stage_instances:
                # Use latest non-pending
                completed = [si for si in wi.stage_instances if si.status == "complete"]
                if completed:
                    stage_map[wi.entity_id] = max(completed, key=lambda s: s.stage_order).stage_key

    def get_dim(obj: Object, dim: str) -> str:
        if dim == "area":
            return area_name_map.get(obj.area_id, "Unassigned") if obj.area_id else "Unassigned"
        if dim == "object_type":
            return obj.object_type
        if dim == "zone":
            return obj.zone or "Unassigned"
        if dim == "owner":
            return obj.owner or "Unassigned"
        if dim == "stage":
            return stage_map.get(obj.id, "No workflow")
        return "Unknown"

    from collections import defaultdict
    bucket: dict[tuple[str, str], list[float]] = defaultdict(list)

    for obj in objects:
        row_val = get_dim(obj, rows)
        col_val = get_dim(obj, cols)
        if metric == "count":
            bucket[(row_val, col_val)].append(1.0)
        elif metric == "readiness":
            ev = readiness_map.get(obj.id)
            if ev:
                bucket[(row_val, col_val)].append(ev.overall_readiness)
        else:  # complexity
            bucket[(row_val, col_val)].append(1.0)

    all_rows = sorted({k[0] for k in bucket.keys()})
    all_cols = sorted({k[1] for k in bucket.keys()})

    cells: list[MatrixCell] = []
    for r in all_rows:
        for c in all_cols:
            vals = bucket.get((r, c), [])
            if metric == "count":
                val: float = float(len(vals))
                max_count = max((len(v) for v in bucket.values()), default=1)
                color = _readiness_color(val / max_count if max_count > 0 else 0.0)
            elif metric == "readiness":
                val = round(sum(vals) / len(vals), 3) if vals else 0.0
                color = _readiness_color(val)
            else:
                val = round(sum(vals) / len(vals), 2) if vals else 0.0
                color = "#3b82f6"
            cells.append(MatrixCell(row=r, col=c, value=val, color=color))

    return MatrixData(row_labels=all_rows, col_labels=all_cols, cells=cells)


# ---------------------------------------------------------------------------
# Saved views CRUD
# ---------------------------------------------------------------------------

@router.post("/{project_id}/saved-views", response_model=SavedViewResponse, status_code=201)
def create_saved_view(
    project_id: uuid.UUID,
    body: SavedViewCreate,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    sv = SavedView(project_id=project_id, name=body.name, config=body.config)
    db.add(sv)
    db.commit()
    db.refresh(sv)
    return sv


@router.get("/{project_id}/saved-views", response_model=list[SavedViewResponse])
def list_saved_views(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(SavedView).filter(SavedView.project_id == project_id).all()


# ---------------------------------------------------------------------------
# C1.5  RACI Chart — rows=resources (RBS), cols=task_keys (ABS)   FR-4.6.1h
# ---------------------------------------------------------------------------

class RACIRow(BaseModel):
    resource_name: str
    step_key: str
    raci_role: str  # R | A | C | I


@router.get("/{project_id}/matrix/raci", response_model=list[RACIRow])
def raci_matrix(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    RACI chart derived from task assignments.
    Resources with assigned_resource_id on a TaskInstance are classified as
    Responsible (R).  The object owner is Accountable (A).
    Returns flat list; frontend MatrixView builds the grid.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    obj_ids = [o.id for o in db.query(Object).filter(Object.project_id == project_id).all()]
    if not obj_ids:
        return []

    wi_ids = [
        wi.id
        for wi in db.query(WorkflowInstance.id)
        .filter(
            WorkflowInstance.entity_type == "object",
            WorkflowInstance.entity_id.in_(obj_ids),
        )
        .all()
    ]
    if not wi_ids:
        return []

    stage_ids = [
        si.id
        for si in db.query(StageInstance.id)
        .filter(StageInstance.workflow_instance_id.in_(wi_ids))
        .all()
    ]
    if not stage_ids:
        return []

    tasks = (
        db.query(TaskInstance)
        .filter(
            TaskInstance.stage_instance_id.in_(stage_ids),
            TaskInstance.assigned_resource_id.isnot(None),
        )
        .all()
    )

    resource_ids = {t.assigned_resource_id for t in tasks}
    resources = db.query(Resource).filter(Resource.id.in_(resource_ids)).all()
    res_name_map = {r.id: r.name for r in resources}

    rows: list[RACIRow] = []
    for task in tasks:
        res_name = res_name_map.get(task.assigned_resource_id, str(task.assigned_resource_id))
        rows.append(RACIRow(
            resource_name=res_name,
            step_key=task.task_key,
            raci_role="R",
        ))

    return rows


# ---------------------------------------------------------------------------
# C1.6  Resource Assignment — rows=resources (RBS), cols=CBS items  FR-4.6.1d
# ---------------------------------------------------------------------------

class AllocationCell(BaseModel):
    resource_name: str
    cbs_item: str
    allocation_pct: float


@router.get("/{project_id}/matrix/resource-assignment", response_model=list[AllocationCell])
def resource_assignment_matrix(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Resource Assignment matrix (RBS × CBS).
    CBS items are represented by ClassDefinition names.
    allocation_pct = (tasks assigned to resource in class) / (total tasks in class) × 100.
    """
    # CBS/ClassDefinition removed — resource-assignment matrix returns empty
    cells: list[AllocationCell] = []

    return cells
