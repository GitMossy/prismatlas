"""
Link Templates API — FR-4.5.4

Full CRUD for LinkTemplate records.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.link_template import LinkTemplate

router = APIRouter(prefix="/link-templates", tags=["link-templates"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LinkTemplateCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    source_object_type: str
    source_stage_key: str | None = None
    target_object_type: str
    target_stage_key: str | None = None
    link_type: str = "FS"
    lag_days: int = 0
    is_active: bool = True


class LinkTemplateUpdate(BaseModel):
    name: str | None = None
    source_object_type: str | None = None
    source_stage_key: str | None = None
    target_object_type: str | None = None
    target_stage_key: str | None = None
    link_type: str | None = None
    lag_days: int | None = None
    is_active: bool | None = None


class LinkTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    source_object_type: str
    source_stage_key: str | None
    target_object_type: str
    target_stage_key: str | None
    link_type: str
    lag_days: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[LinkTemplateResponse])
def list_link_templates(
    project_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(LinkTemplate)
    if project_id:
        q = q.filter(LinkTemplate.project_id == project_id)
    if is_active is not None:
        q = q.filter(LinkTemplate.is_active == is_active)
    return q.order_by(LinkTemplate.name).all()


@router.post("", response_model=LinkTemplateResponse, status_code=201)
def create_link_template(body: LinkTemplateCreate, db: Session = Depends(get_db)):
    tmpl = LinkTemplate(**body.model_dump())
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.get("/{template_id}", response_model=LinkTemplateResponse)
def get_link_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    tmpl = db.query(LinkTemplate).filter(LinkTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Link template not found")
    return tmpl


@router.put("/{template_id}", response_model=LinkTemplateResponse)
def update_link_template(
    template_id: uuid.UUID,
    body: LinkTemplateUpdate,
    db: Session = Depends(get_db),
):
    tmpl = db.query(LinkTemplate).filter(LinkTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Link template not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tmpl, field, value)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}", status_code=204)
def delete_link_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    tmpl = db.query(LinkTemplate).filter(LinkTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Link template not found")
    db.delete(tmpl)
    db.commit()
