"""
Effort Estimation Matrix API — FR-4.3.3

Provides CRUD for EffortMatrixCell rows.  The matrix is keyed on
(workflow_template_id, step_key); the UI renders it as a grid where rows
are templates/Types and columns are step keys.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.effort_matrix import EffortMatrixCell

router = APIRouter(prefix="/effort-matrix", tags=["effort-matrix"])


class EffortMatrixCellCreate(BaseModel):
    workflow_template_id: uuid.UUID
    step_key: str
    step_name: str | None = None
    base_effort_hours: float = 0.0
    notes: str | None = None


class EffortMatrixCellUpdate(BaseModel):
    step_name: str | None = None
    base_effort_hours: float | None = None
    notes: str | None = None


class EffortMatrixCellResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_template_id: uuid.UUID
    step_key: str
    step_name: str | None
    base_effort_hours: float
    notes: str | None


@router.get("", response_model=list[EffortMatrixCellResponse])
def list_cells(
    workflow_template_id: uuid.UUID | None = None,
    step_key: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(EffortMatrixCell)
    if workflow_template_id:
        q = q.filter(EffortMatrixCell.workflow_template_id == workflow_template_id)
    if step_key:
        q = q.filter(EffortMatrixCell.step_key == step_key)
    return q.all()


@router.post("", response_model=EffortMatrixCellResponse, status_code=201)
def upsert_cell(body: EffortMatrixCellCreate, db: Session = Depends(get_db)):
    """
    Create or update a matrix cell.  If a cell for the given
    (workflow_template_id, step_key) pair already exists, it is updated.
    """
    existing = (
        db.query(EffortMatrixCell)
        .filter(
            EffortMatrixCell.workflow_template_id == body.workflow_template_id,
            EffortMatrixCell.step_key == body.step_key,
        )
        .first()
    )
    if existing:
        if body.step_name is not None:
            existing.step_name = body.step_name
        existing.base_effort_hours = body.base_effort_hours
        if body.notes is not None:
            existing.notes = body.notes
        db.commit()
        db.refresh(existing)
        return existing

    cell = EffortMatrixCell(**body.model_dump())
    db.add(cell)
    db.commit()
    db.refresh(cell)
    return cell


@router.get("/{cell_id}", response_model=EffortMatrixCellResponse)
def get_cell(cell_id: uuid.UUID, db: Session = Depends(get_db)):
    cell = db.query(EffortMatrixCell).filter(EffortMatrixCell.id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Effort matrix cell not found")
    return cell


@router.patch("/{cell_id}", response_model=EffortMatrixCellResponse)
def update_cell(cell_id: uuid.UUID, body: EffortMatrixCellUpdate, db: Session = Depends(get_db)):
    cell = db.query(EffortMatrixCell).filter(EffortMatrixCell.id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Effort matrix cell not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cell, field, value)
    db.commit()
    db.refresh(cell)
    return cell


@router.delete("/{cell_id}", status_code=204)
def delete_cell(cell_id: uuid.UUID, db: Session = Depends(get_db)):
    cell = db.query(EffortMatrixCell).filter(EffortMatrixCell.id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Effort matrix cell not found")
    db.delete(cell)
    db.commit()
