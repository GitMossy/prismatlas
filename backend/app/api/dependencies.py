import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.dependency import DependencyRule, Relationship
from app.engines import triggers
from app.engines.cycle_detection import assert_no_cycle
from app.schemas.dependency import (
    DependencyRuleCreate, DependencyRuleResponse,
    RelationshipCreate, RelationshipResponse,
)

rules_router = APIRouter(prefix="/dependency-rules", tags=["dependencies"])
relationships_router = APIRouter(prefix="/relationships", tags=["relationships"])
entities_router = APIRouter(prefix="/entities", tags=["entity-dependencies"])


# --- Dependency Rules ---

@rules_router.get("", response_model=list[DependencyRuleResponse])
def list_rules(
    template_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(DependencyRule)
    if template_id:
        q = q.filter(DependencyRule.template_version_id == template_id)
    if project_id:
        q = q.filter(DependencyRule.project_id == project_id)
    return q.all()


@rules_router.post("", response_model=DependencyRuleResponse, status_code=201)
def create_rule(body: DependencyRuleCreate, db: Session = Depends(get_db)):
    # FR-4.5.3: Reject entity-level rules that would create a dependency cycle
    if body.source_entity_id is not None and body.target_entity_id is not None:
        try:
            assert_no_cycle(body.source_entity_id, body.target_entity_id, db)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    rule = DependencyRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    triggers.on_dependency_rule_changed(rule, db)
    return rule


@rules_router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: uuid.UUID, db: Session = Depends(get_db)):
    rule = db.query(DependencyRule).filter(DependencyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Dependency rule not found")
    # Capture rule data before deletion so trigger can identify affected entities
    rule_snapshot = DependencyRule(
        source_entity_type=rule.source_entity_type,
        source_entity_id=rule.source_entity_id,
        target_entity_type=rule.target_entity_type,
        target_entity_id=rule.target_entity_id,
        name=rule.name,
        condition=rule.condition,
        is_mandatory=rule.is_mandatory,
    )
    db.delete(rule)
    db.commit()
    triggers.on_dependency_rule_changed(rule_snapshot, db)


# --- Relationships ---

@relationships_router.get("", response_model=list[RelationshipResponse])
def list_relationships(
    source_entity_id: uuid.UUID | None = None,
    target_entity_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Relationship)
    if source_entity_id:
        q = q.filter(Relationship.source_entity_id == source_entity_id)
    if target_entity_id:
        q = q.filter(Relationship.target_entity_id == target_entity_id)
    return q.all()


@relationships_router.post("", response_model=RelationshipResponse, status_code=201)
def create_relationship(body: RelationshipCreate, db: Session = Depends(get_db)):
    # FR-4.5.3: Reject relationships that would create a dependency cycle
    try:
        assert_no_cycle(body.source_entity_id, body.target_entity_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    rel = Relationship(**body.model_dump())
    db.add(rel)
    db.commit()
    db.refresh(rel)
    triggers.on_relationship_changed(rel.source_entity_type, rel.source_entity_id, rel.target_entity_id, db)
    return rel


@relationships_router.delete("/{relationship_id}", status_code=204)
def delete_relationship(relationship_id: uuid.UUID, db: Session = Depends(get_db)):
    rel = db.query(Relationship).filter(Relationship.id == relationship_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    source_type, source_id, target_id = rel.source_entity_type, rel.source_entity_id, rel.target_entity_id
    db.delete(rel)
    db.commit()
    triggers.on_relationship_changed(source_type, source_id, target_id, db)


# --- Entity dependency queries ---

@entities_router.get("/{entity_id}/dependencies", response_model=list[RelationshipResponse])
def get_entity_dependencies(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    """What this entity depends on (outbound relationships)."""
    return db.query(Relationship).filter(Relationship.source_entity_id == entity_id).all()


@entities_router.get("/{entity_id}/blocks", response_model=list[RelationshipResponse])
def get_entity_blocks(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    """What this entity is blocking (inbound relationships)."""
    return db.query(Relationship).filter(Relationship.target_entity_id == entity_id).all()
