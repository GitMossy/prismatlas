"""
Export API — FR-4.6.5

Endpoints:
  GET /projects/{project_id}/export/objects.csv
      Export all objects in a project as CSV.

  GET /projects/{project_id}/export/tasks.csv
      Export all task instances (with CPM dates) across all workflow instances.

  GET /projects/{project_id}/export/readiness.csv
      Export readiness evaluations for all objects.
"""
import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.object import Object
from app.models.readiness import ReadinessEvaluation
from app.models.workflow import WorkflowInstance, StageInstance, TaskInstance

router = APIRouter(prefix="/projects", tags=["export"])


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    if not rows:
        content = ""
    else:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        content = buffer.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/export/objects.csv")
def export_objects(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Export all objects in a project as CSV."""
    objects = (
        db.query(Object)
        .filter(Object.project_id == project_id)
        .order_by(Object.name)
        .all()
    )
    rows = [
        {
            "id": str(obj.id),
            "name": obj.name,
            "object_type": obj.object_type,
            "status": obj.status,
            "zone": obj.zone or "",
            "owner": obj.owner or "",
            "planned_start": str(obj.planned_start) if obj.planned_start else "",
            "planned_end": str(obj.planned_end) if obj.planned_end else "",
            "area_id": str(obj.area_id) if obj.area_id else "",
            "unit_id": str(obj.unit_id) if obj.unit_id else "",
        }
        for obj in objects
    ]
    return _csv_response(rows, f"objects_{project_id}.csv")


@router.get("/{project_id}/export/tasks.csv")
def export_tasks(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Export all task instances (with CPM schedule dates) for a project."""
    objects = db.query(Object).filter(Object.project_id == project_id).all()
    object_ids = [o.id for o in objects]
    object_name_map = {o.id: o.name for o in objects}

    instances = (
        db.query(WorkflowInstance)
        .filter(
            WorkflowInstance.entity_type == "object",
            WorkflowInstance.entity_id.in_(object_ids),
        )
        .all()
    )

    rows = []
    for inst in instances:
        obj_name = object_name_map.get(inst.entity_id, str(inst.entity_id))
        for stage in sorted(inst.stage_instances, key=lambda s: s.stage_order):
            for task in sorted(stage.task_instances, key=lambda t: t.task_order):
                rows.append({
                    "object_id": str(inst.entity_id),
                    "object_name": obj_name,
                    "workflow_instance_id": str(inst.id),
                    "stage_key": stage.stage_key,
                    "stage_name": stage.stage_name,
                    "stage_status": stage.status,
                    "task_key": task.task_key,
                    "task_name": task.task_name,
                    "task_status": task.status,
                    "is_mandatory": task.is_mandatory,
                    "duration_days": task.duration_days if task.duration_days is not None else "",
                    "effort_hours": task.effort_hours if task.effort_hours is not None else "",
                    "early_start": task.early_start if task.early_start is not None else "",
                    "early_finish": task.early_finish if task.early_finish is not None else "",
                    "late_start": task.late_start if task.late_start is not None else "",
                    "late_finish": task.late_finish if task.late_finish is not None else "",
                    "total_float": task.total_float if task.total_float is not None else "",
                    "is_critical": task.is_critical,
                    "completed_at": str(task.completed_at) if task.completed_at else "",
                    "completed_by": task.completed_by or "",
                })

    return _csv_response(rows, f"tasks_{project_id}.csv")


@router.get("/{project_id}/export/readiness.csv")
def export_readiness(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Export readiness evaluations for all objects in a project."""
    objects = db.query(Object).filter(Object.project_id == project_id).all()
    object_ids = [o.id for o in objects]
    object_name_map = {o.id: o.name for o in objects}

    evals = (
        db.query(ReadinessEvaluation)
        .filter(
            ReadinessEvaluation.entity_type == "object",
            ReadinessEvaluation.entity_id.in_(object_ids),
        )
        .all()
    )

    rows = [
        {
            "object_id": str(ev.entity_id),
            "object_name": object_name_map.get(ev.entity_id, str(ev.entity_id)),
            "technical_readiness": ev.technical_readiness,
            "document_readiness": ev.document_readiness,
            "stage_readiness": ev.stage_readiness,
            "overall_readiness": ev.overall_readiness,
            "ready_for_fat": ev.ready_for_fat,
            "ready_for_sat": ev.ready_for_sat,
            "blocker_count": len(ev.blockers) if ev.blockers else 0,
            "next_action": ev.next_action or "",
            "evaluated_at": str(ev.evaluated_at),
        }
        for ev in evals
    ]
    return _csv_response(rows, f"readiness_{project_id}.csv")
