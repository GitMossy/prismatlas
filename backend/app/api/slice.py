import uuid
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.object import Object
from app.models.readiness import ReadinessEvaluation
from app.models.workflow import WorkflowInstance, StageInstance
from app.schemas.slice import SliceQuery, SliceResponse, SliceResultItem

router = APIRouter(prefix="/projects", tags=["slice"])


@router.post("/{project_id}/slice", response_model=SliceResponse)
def query_slice(project_id: uuid.UUID, body: SliceQuery, db: Session = Depends(get_db)):
    # Build filtered object query
    q = db.query(Object).filter(Object.project_id == project_id)
    if body.zone:
        q = q.filter(Object.zone == body.zone)
    if body.owner:
        q = q.filter(Object.owner == body.owner)
    if body.object_type:
        q = q.filter(Object.object_type == body.object_type)
    if body.planned_after:
        q = q.filter(Object.planned_start >= body.planned_after)
    if body.planned_before:
        q = q.filter(Object.planned_end <= body.planned_before)
    if body.stage:
        active_ids = (
            db.query(WorkflowInstance.entity_id)
            .join(StageInstance, StageInstance.workflow_instance_id == WorkflowInstance.id)
            .filter(
                WorkflowInstance.entity_type == "object",
                StageInstance.stage_key == body.stage,
                StageInstance.status == "active",
            )
            .subquery()
        )
        q = q.filter(Object.id.in_(active_ids))

    objects = q.all()
    object_ids = [o.id for o in objects]

    # Bulk load latest readiness evaluations (one query)
    # For each entity_id, get the most recent evaluation via a subquery
    from sqlalchemy import func

    latest_eval_subq = (
        db.query(
            ReadinessEvaluation.entity_id,
            func.max(ReadinessEvaluation.evaluated_at).label("max_at"),
        )
        .filter(ReadinessEvaluation.entity_id.in_(object_ids))
        .group_by(ReadinessEvaluation.entity_id)
        .subquery()
    )
    evaluations = (
        db.query(ReadinessEvaluation)
        .join(
            latest_eval_subq,
            (ReadinessEvaluation.entity_id == latest_eval_subq.c.entity_id)
            & (ReadinessEvaluation.evaluated_at == latest_eval_subq.c.max_at),
        )
        .all()
    )
    eval_map: dict[uuid.UUID, ReadinessEvaluation] = {ev.entity_id: ev for ev in evaluations}

    # Bulk load active stage instances (one query)
    # Join WorkflowInstance → StageInstance filtered to active stages for these objects
    active_stages = (
        db.query(WorkflowInstance.entity_id, StageInstance.stage_key)
        .join(StageInstance, StageInstance.workflow_instance_id == WorkflowInstance.id)
        .filter(
            WorkflowInstance.entity_type == "object",
            WorkflowInstance.entity_id.in_(object_ids),
            StageInstance.status == "active",
        )
        .all()
    )
    # If an entity has multiple active stages take the first one found
    stage_map: dict[uuid.UUID, str] = {}
    for entity_id, stage_key in active_stages:
        if entity_id not in stage_map:
            stage_map[entity_id] = stage_key

    # Build results
    results: list[SliceResultItem] = []
    blocker_type_counter: Counter = Counter()

    for obj in objects:
        ev = eval_map.get(obj.id)
        overall_readiness = ev.overall_readiness if ev else 0.0
        ready_for_fat = ev.ready_for_fat if ev else False
        ready_for_sat = ev.ready_for_sat if ev else False
        blockers = ev.blockers if ev else []
        blocker_count = len(blockers)
        top_blocker: str | None = blockers[0]["reason"] if blockers else None

        for b in blockers:
            blocker_type_counter[b.get("type", "unknown")] += 1

        results.append(SliceResultItem(
            entity_id=obj.id,
            entity_name=obj.name,
            zone=obj.zone,
            owner=obj.owner,
            object_type=obj.object_type,
            planned_start=obj.planned_start,
            planned_end=obj.planned_end,
            current_stage=stage_map.get(obj.id),
            overall_readiness=overall_readiness,
            ready_for_fat=ready_for_fat,
            ready_for_sat=ready_for_sat,
            blocker_count=blocker_count,
            top_blocker=top_blocker,
        ))

    total = len(results)
    avg_readiness = sum(r.overall_readiness for r in results) / total if total else 0.0
    fat_ready_count = sum(1 for r in results if r.ready_for_fat)
    sat_ready_count = sum(1 for r in results if r.ready_for_sat)
    total_blockers = sum(r.blocker_count for r in results)
    common_blocker_types = [t for t, _ in blocker_type_counter.most_common(5)]

    return SliceResponse(
        query=body.model_dump(mode="json"),
        total=total,
        results=results,
        avg_readiness=avg_readiness,
        fat_ready_count=fat_ready_count,
        sat_ready_count=sat_ready_count,
        total_blockers=total_blockers,
        common_blocker_types=common_blocker_types,
    )
