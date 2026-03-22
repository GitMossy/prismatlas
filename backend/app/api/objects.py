import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines import link_template_applier
from app.models.object import Object
from app.models.workflow import WorkflowInstance, StageInstance
from app.schemas.object import ObjectCreate, ObjectUpdate, ObjectResponse

router = APIRouter(prefix="/objects", tags=["objects"])


@router.get("", response_model=list[ObjectResponse])
def list_objects(
    project_id: uuid.UUID | None = None,
    area_id: uuid.UUID | None = None,
    unit_id: uuid.UUID | None = None,
    parent_object_id: uuid.UUID | None = None,
    type: str | None = None,
    status: str | None = None,
    zone: str | None = None,
    owner: str | None = None,
    planned_after: date | None = None,
    planned_before: date | None = None,
    stage: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Object)
    if project_id:
        q = q.filter(Object.project_id == project_id)
    if area_id:
        q = q.filter(Object.area_id == area_id)
    if unit_id:
        q = q.filter(Object.unit_id == unit_id)
    if parent_object_id:
        q = q.filter(Object.parent_object_id == parent_object_id)
    if type:
        q = q.filter(Object.object_type == type)
    if status:
        q = q.filter(Object.status == status)
    if zone:
        q = q.filter(Object.zone == zone)
    if owner:
        q = q.filter(Object.owner == owner)
    if planned_after:
        q = q.filter(Object.planned_start >= planned_after)
    if planned_before:
        q = q.filter(Object.planned_end <= planned_before)
    if stage:
        active_ids = (
            db.query(WorkflowInstance.entity_id)
            .join(StageInstance, StageInstance.workflow_instance_id == WorkflowInstance.id)
            .filter(
                WorkflowInstance.entity_type == "object",
                StageInstance.stage_key == stage,
                StageInstance.status == "active",
            )
            .subquery()
        )
        q = q.filter(Object.id.in_(active_ids))
    return q.all()


@router.post("", response_model=ObjectResponse, status_code=201)
def create_object(body: ObjectCreate, db: Session = Depends(get_db)):
    obj = Object(**body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    # FR-4.5.4: Auto-apply any matching active LinkTemplates for this project
    link_template_applier.apply(obj, db)
    return obj


@router.get("/{object_id}", response_model=ObjectResponse)
def get_object(object_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.query(Object).filter(Object.id == object_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


@router.put("/{object_id}", response_model=ObjectResponse)
def update_object(object_id: uuid.UUID, body: ObjectUpdate, db: Session = Depends(get_db)):
    obj = db.query(Object).filter(Object.id == object_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{object_id}", status_code=204)
def delete_object(object_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.query(Object).filter(Object.id == object_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    # Cascade: SQLAlchemy will handle child_objects (SET NULL) and workflow/readiness rows
    db.delete(obj)
    db.commit()
