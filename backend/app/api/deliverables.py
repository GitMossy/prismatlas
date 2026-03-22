import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines import triggers
from app.models.deliverable import Deliverable
from app.schemas.deliverable import DeliverableCreate, DeliverableResponse, DeliverableUpdate

router = APIRouter(prefix="/deliverables", tags=["deliverables"])


@router.get("", response_model=list[DeliverableResponse])
def list_deliverables(
    project_id: uuid.UUID | None = None,
    task_instance_id: uuid.UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Deliverable)
    if project_id:
        q = q.filter(Deliverable.project_id == project_id)
    if task_instance_id:
        q = q.filter(Deliverable.task_instance_id == task_instance_id)
    if status:
        q = q.filter(Deliverable.status == status)
    return q.order_by(Deliverable.due_date.asc().nullslast(), Deliverable.name).all()


@router.post("", response_model=DeliverableResponse, status_code=201)
def create_deliverable(body: DeliverableCreate, db: Session = Depends(get_db)):
    deliverable = Deliverable(**body.model_dump())
    db.add(deliverable)
    db.commit()
    db.refresh(deliverable)
    return deliverable


@router.get("/{deliverable_id}", response_model=DeliverableResponse)
def get_deliverable(deliverable_id: uuid.UUID, db: Session = Depends(get_db)):
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return deliverable


@router.put("/{deliverable_id}", response_model=DeliverableResponse)
def update_deliverable(
    deliverable_id: uuid.UUID,
    body: DeliverableUpdate,
    db: Session = Depends(get_db),
):
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    old_status = deliverable.status
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(deliverable, field, value)

    # Auto-set approved_at when transitioning to 'approved'
    if (
        deliverable.status == "approved"
        and old_status != "approved"
        and deliverable.approved_at is None
    ):
        deliverable.approved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(deliverable)

    # Re-evaluate entity readiness if status changed
    if deliverable.status != old_status:
        triggers.on_deliverable_status_changed(deliverable_id, db)

    return deliverable


@router.delete("/{deliverable_id}", status_code=204)
def delete_deliverable(deliverable_id: uuid.UUID, db: Session = Depends(get_db)):
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    db.delete(deliverable)
    db.commit()
