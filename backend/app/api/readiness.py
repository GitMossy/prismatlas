import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.readiness import ReadinessEvaluation
from app.models.object import Object
from app.models.document import Document
from app.models.project import Area
from app.models.dependency import DependencyRule
from app.schemas.readiness import ReadinessResponse, ProjectReadinessSummaryItem, AreaReadinessSummary
from app.engines import readiness as readiness_engine
from app.engines.dependency import evaluate_condition

entities_router = APIRouter(prefix="/entities", tags=["readiness"])
projects_router = APIRouter(prefix="/projects", tags=["readiness"])


def _get_latest_readiness(entity_id: uuid.UUID, db: Session) -> ReadinessEvaluation:
    evaluation = (
        db.query(ReadinessEvaluation)
        .filter(ReadinessEvaluation.entity_id == entity_id)
        .order_by(ReadinessEvaluation.evaluated_at.desc())
        .first()
    )
    if not evaluation:
        raise HTTPException(
            status_code=404,
            detail="No readiness evaluation found. Trigger a re-evaluation first.",
        )
    return evaluation


def _build_eval_map(entity_ids: list[uuid.UUID], db: Session) -> dict[uuid.UUID, ReadinessEvaluation]:
    """Return the latest ReadinessEvaluation per entity_id in a single query."""
    if not entity_ids:
        return {}
    latest_subq = (
        db.query(
            ReadinessEvaluation.entity_id,
            func.max(ReadinessEvaluation.evaluated_at).label("max_at"),
        )
        .filter(ReadinessEvaluation.entity_id.in_(entity_ids))
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


@entities_router.post("/{entity_id}/readiness/evaluate", response_model=ReadinessResponse)
def evaluate_readiness(entity_id: uuid.UUID, entity_type: str, db: Session = Depends(get_db)):
    """
    Manually trigger a readiness re-evaluation for an entity.
    entity_type query param: "object" or "document"
    """
    return readiness_engine.evaluate_entity(entity_type, entity_id, db)


@entities_router.get("/{entity_id}/readiness", response_model=ReadinessResponse)
def get_readiness(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Returns the latest readiness evaluation for an entity.
    Readiness is always derived — see Phase 3 for the calculation engine.
    """
    return _get_latest_readiness(entity_id, db)


class DependencyRuleDetail(BaseModel):
    id: uuid.UUID
    name: str
    target_entity_id: uuid.UUID
    target_entity_name: str
    target_entity_status: str | None
    condition: dict[str, Any]
    is_mandatory: bool
    link_type: str
    lag_days: float
    satisfied: bool
    reason: str | None


@entities_router.get("/{entity_id}/dependency-rules", response_model=list[DependencyRuleDetail])
def list_entity_dependency_rules(
    entity_id: uuid.UUID,
    entity_type: str = Query(default="object"),
    db: Session = Depends(get_db),
):
    """Return all cross-object DependencyRules where this entity is the source, with live satisfaction status."""
    rules = (
        db.query(DependencyRule)
        .filter(
            DependencyRule.source_entity_type == entity_type,
            DependencyRule.source_entity_id == entity_id,
            DependencyRule.target_entity_id.isnot(None),
            DependencyRule.target_entity_type == "object",
        )
        .all()
    )
    results = []
    for rule in rules:
        target_obj = db.query(Object).filter(Object.id == rule.target_entity_id).first()
        if not target_obj:
            continue
        satisfied, reason = evaluate_condition(rule.condition, rule.target_entity_type, rule.target_entity_id, db)
        results.append(DependencyRuleDetail(
            id=rule.id,
            name=rule.name,
            target_entity_id=rule.target_entity_id,
            target_entity_name=target_obj.name,
            target_entity_status=target_obj.status,
            condition=rule.condition,
            is_mandatory=rule.is_mandatory,
            link_type=rule.link_type,
            lag_days=rule.lag_days,
            satisfied=satisfied,
            reason=reason if not satisfied else None,
        ))
    return results


@entities_router.get("/{entity_id}/blockers")
def get_blockers(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    """Returns only the blockers list from the latest readiness evaluation."""
    evaluation = _get_latest_readiness(entity_id, db)
    return {"entity_id": entity_id, "blockers": evaluation.blockers}


@projects_router.get("/{project_id}/readiness-summary", response_model=list[ProjectReadinessSummaryItem])
def project_readiness_summary(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Rollup of readiness across all objects and documents in a project."""
    objects = db.query(Object).filter(Object.project_id == project_id).all()
    documents = db.query(Document).filter(Document.project_id == project_id).all()

    all_ids = [o.id for o in objects] + [d.id for d in documents]
    eval_map = _build_eval_map(all_ids, db)

    result = []
    for obj in objects:
        ev = eval_map.get(obj.id)
        result.append(ProjectReadinessSummaryItem(
            entity_id=obj.id,
            entity_name=obj.name,
            entity_type="object",
            object_type=obj.object_type,
            overall_readiness=ev.overall_readiness if ev else 0.0,
            ready_for_fat=ev.ready_for_fat if ev else False,
            ready_for_sat=ev.ready_for_sat if ev else False,
            blocker_count=len(ev.blockers) if ev else 0,
        ))
    for doc in documents:
        ev = eval_map.get(doc.id)
        result.append(ProjectReadinessSummaryItem(
            entity_id=doc.id,
            entity_name=doc.name,
            entity_type="document",
            object_type=doc.document_type,
            overall_readiness=ev.overall_readiness if ev else 0.0,
            ready_for_fat=ev.ready_for_fat if ev else False,
            ready_for_sat=ev.ready_for_sat if ev else False,
            blocker_count=len(ev.blockers) if ev else 0,
        ))
    return result


@projects_router.get("/{project_id}/area-summary", response_model=list[AreaReadinessSummary])
def project_area_summary(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Per-area readiness aggregates — object count, avg readiness, FAT/SAT ready counts, blocker count."""
    areas = db.query(Area).filter(Area.project_id == project_id).all()
    result = []
    for area in areas:
        objects = db.query(Object).filter(Object.area_id == area.id).all()
        eval_map = _build_eval_map([o.id for o in objects], db)
        evals = [eval_map[o.id] for o in objects if o.id in eval_map]
        result.append(AreaReadinessSummary(
            area_id=area.id,
            area_name=area.name,
            object_count=len(objects),
            avg_readiness=sum(e.overall_readiness for e in evals) / len(evals) if evals else 0.0,
            fat_ready_count=sum(1 for e in evals if e.ready_for_fat),
            sat_ready_count=sum(1 for e in evals if e.ready_for_sat),
            blocker_count=sum(len(e.blockers) for e in evals),
        ))
    return sorted(result, key=lambda r: r.avg_readiness)


@projects_router.get("/{project_id}/fat-readiness", response_model=list[ProjectReadinessSummaryItem])
def project_fat_readiness(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """All objects in the project with their FAT readiness status."""
    objects = db.query(Object).filter(Object.project_id == project_id).all()
    eval_map = _build_eval_map([o.id for o in objects], db)

    return [
        ProjectReadinessSummaryItem(
            entity_id=obj.id,
            entity_name=obj.name,
            entity_type="object",
            object_type=obj.object_type,
            overall_readiness=(ev := eval_map.get(obj.id)) and ev.overall_readiness or 0.0,
            ready_for_fat=eval_map.get(obj.id) and eval_map[obj.id].ready_for_fat or False,
            ready_for_sat=eval_map.get(obj.id) and eval_map[obj.id].ready_for_sat or False,
            blocker_count=len(eval_map[obj.id].blockers) if obj.id in eval_map else 0,
        )
        for obj in objects
    ]


@projects_router.get("/{project_id}/sat-readiness", response_model=list[ProjectReadinessSummaryItem])
def project_sat_readiness(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """All objects in the project with their SAT readiness status."""
    objects = db.query(Object).filter(Object.project_id == project_id).all()
    eval_map = _build_eval_map([o.id for o in objects], db)

    return [
        ProjectReadinessSummaryItem(
            entity_id=obj.id,
            entity_name=obj.name,
            entity_type="object",
            object_type=obj.object_type,
            overall_readiness=eval_map[obj.id].overall_readiness if obj.id in eval_map else 0.0,
            ready_for_fat=eval_map[obj.id].ready_for_fat if obj.id in eval_map else False,
            ready_for_sat=eval_map[obj.id].ready_for_sat if obj.id in eval_map else False,
            blocker_count=len(eval_map[obj.id].blockers) if obj.id in eval_map else 0,
        )
        for obj in objects
    ]
