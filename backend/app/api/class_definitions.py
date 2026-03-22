import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.class_definition import ClassDefinition
from app.models.workflow import WorkflowInstance, WorkflowTemplateVersion
from app.schemas.class_definition import (
    ClassDefinitionCreate,
    ClassDefinitionResponse,
    ClassDefinitionUpdate,
)


class ClassInstantiateRequest(BaseModel):
    project_id: uuid.UUID | None = None


class ClassInstantiateResponse(BaseModel):
    workflow_instance_ids: list[uuid.UUID]

router = APIRouter(prefix="/class-definitions", tags=["class-definitions"])


@router.get("", response_model=list[ClassDefinitionResponse])
def list_class_definitions(
    project_id: uuid.UUID | None = None,
    area_id: uuid.UUID | None = None,
    object_type: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(ClassDefinition)
    if project_id:
        q = q.filter(ClassDefinition.project_id == project_id)
    if area_id:
        q = q.filter(ClassDefinition.area_id == area_id)
    if object_type:
        q = q.filter(ClassDefinition.object_type == object_type)
    return q.order_by(ClassDefinition.name).all()


@router.post("", response_model=ClassDefinitionResponse, status_code=201)
def create_class_definition(body: ClassDefinitionCreate, db: Session = Depends(get_db)):
    cls = ClassDefinition(**body.model_dump())
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return cls


@router.get("/{class_id}", response_model=ClassDefinitionResponse)
def get_class_definition(class_id: uuid.UUID, db: Session = Depends(get_db)):
    cls = db.query(ClassDefinition).filter(ClassDefinition.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class definition not found")
    return cls


@router.put("/{class_id}", response_model=ClassDefinitionResponse)
def update_class_definition(
    class_id: uuid.UUID, body: ClassDefinitionUpdate, db: Session = Depends(get_db)
):
    cls = db.query(ClassDefinition).filter(ClassDefinition.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class definition not found")
    updated_fields = body.model_dump(exclude_unset=True)
    for field, value in updated_fields.items():
        setattr(cls, field, value)
    db.commit()
    db.refresh(cls)
    if 'workflow_template_id' in updated_fields:
        from app.engines.triggers import on_class_definition_changed
        on_class_definition_changed(class_id, db)
    return cls


@router.delete("/{class_id}", status_code=204)
def delete_class_definition(class_id: uuid.UUID, db: Session = Depends(get_db)):
    cls = db.query(ClassDefinition).filter(ClassDefinition.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class definition not found")
    db.delete(cls)
    db.commit()


@router.post("/{class_id}/instantiate", response_model=ClassInstantiateResponse, status_code=201)
def instantiate_class_definition(
    class_id: uuid.UUID,
    body: ClassInstantiateRequest,
    db: Session = Depends(get_db),
):
    """
    FR-4.3.5, BR-5.5 — Create instance_count WorkflowInstances for a ClassDefinition.

    Effort scaling is applied to the template's effort_matrix (if present) using
    effort_scaling_mode:
      linear  — base_hours × instance_count × complexity
      sqrt    — base_hours × sqrt(instance_count) × complexity
      fixed   — base_hours (no scaling)

    Returns the IDs of all created WorkflowInstances.
    """
    cls = db.query(ClassDefinition).filter(ClassDefinition.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class definition not found")

    if not cls.workflow_template_id:
        raise HTTPException(
            status_code=422,
            detail="Class definition has no workflow_template_id — cannot instantiate",
        )

    # Find the active template version
    template_version = (
        db.query(WorkflowTemplateVersion)
        .filter(
            WorkflowTemplateVersion.template_id == cls.workflow_template_id,
            WorkflowTemplateVersion.is_active.is_(True),
        )
        .order_by(WorkflowTemplateVersion.version_number.desc())
        .first()
    )
    if not template_version:
        raise HTTPException(
            status_code=422,
            detail="No active version found for the linked workflow template",
        )

    # Determine project_id: body override or class definition's own project_id
    project_id = body.project_id if body.project_id is not None else cls.project_id

    # Compute scaled effort from template definition's effort_matrix (if present)
    definition = template_version.definition or {}
    effort_matrix: dict = definition.get("effort_matrix", {})
    scaling_mode = cls.effort_scaling_mode
    count = cls.instance_count
    complexity = cls.complexity

    scaled_effort_matrix: dict = {}
    for step_key, base_hours in effort_matrix.items():
        if scaling_mode == "linear":
            scaled = base_hours * count * complexity
        elif scaling_mode == "sqrt":
            scaled = base_hours * math.sqrt(count) * complexity
        else:  # fixed
            scaled = base_hours
        scaled_effort_matrix[step_key] = scaled

    # Create instance_count WorkflowInstances, each with entity_type='object'
    # and entity_id=cls.id (placeholder until actual objects are assigned)
    created_ids: list[uuid.UUID] = []
    now = datetime.now(timezone.utc)
    for _ in range(count):
        wi = WorkflowInstance(
            entity_type="object",
            entity_id=cls.id,
            template_version_id=template_version.id,
            status="active",
        )
        db.add(wi)
        db.flush()  # populate wi.id
        created_ids.append(wi.id)

    db.commit()
    return ClassInstantiateResponse(workflow_instance_ids=created_ids)
