import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.project import Project, Area, Unit
from app.models.object import Object
from app.schemas.project import (
    ProjectCreate, ProjectResponse,
    AreaCreate, AreaResponse,
    UnitCreate, UnitResponse,
)


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class AreaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class UnitUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

router = APIRouter(prefix="/projects", tags=["projects"])
areas_router = APIRouter(prefix="/areas", tags=["areas"])
units_router = APIRouter(prefix="/units", tags=["units"])


# --- Projects ---

@router.get("", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    return db.query(Project).filter(Project.created_by == uuid.UUID(user_id)).all()


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    project = Project(**body.model_dump(), created_by=uuid.UUID(user_id))
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.created_by == uuid.UUID(user_id)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: uuid.UUID, body: ProjectUpdate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.created_by == uuid.UUID(user_id)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.created_by == uuid.UUID(user_id)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()


# --- Areas ---

@areas_router.get("", response_model=list[AreaResponse])
def list_areas(project_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    q = db.query(Area)
    if project_id:
        q = q.filter(Area.project_id == project_id)
    return q.all()


@areas_router.post("", response_model=AreaResponse, status_code=201)
def create_area(body: AreaCreate, db: Session = Depends(get_db)):
    if not db.query(Project).filter(Project.id == body.project_id).first():
        raise HTTPException(status_code=404, detail="Project not found")
    area = Area(**body.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@areas_router.get("/{area_id}", response_model=AreaResponse)
def get_area(area_id: uuid.UUID, db: Session = Depends(get_db)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return area


@areas_router.put("/{area_id}", response_model=AreaResponse)
def update_area(area_id: uuid.UUID, body: AreaUpdate, db: Session = Depends(get_db)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(area, field, value)
    db.commit()
    db.refresh(area)
    return area


@areas_router.delete("/{area_id}", status_code=204)
def delete_area(area_id: uuid.UUID, db: Session = Depends(get_db)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    # Null out FK references on objects before deleting (no DB-level cascade)
    unit_ids = [u.id for u in area.units]
    if unit_ids:
        db.query(Object).filter(Object.unit_id.in_(unit_ids)).update(
            {Object.unit_id: None, Object.area_id: None}, synchronize_session=False
        )
    db.query(Object).filter(Object.area_id == area_id).update(
        {Object.area_id: None}, synchronize_session=False
    )
    db.delete(area)
    db.commit()


# --- Units ---

@units_router.get("", response_model=list[UnitResponse])
def list_units(area_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    q = db.query(Unit)
    if area_id:
        q = q.filter(Unit.area_id == area_id)
    return q.all()


@units_router.post("", response_model=UnitResponse, status_code=201)
def create_unit(body: UnitCreate, db: Session = Depends(get_db)):
    if not db.query(Area).filter(Area.id == body.area_id).first():
        raise HTTPException(status_code=404, detail="Area not found")
    unit = Unit(**body.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@units_router.get("/{unit_id}", response_model=UnitResponse)
def get_unit(unit_id: uuid.UUID, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@units_router.put("/{unit_id}", response_model=UnitResponse)
def update_unit(unit_id: uuid.UUID, body: UnitUpdate, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(unit, field, value)
    db.commit()
    db.refresh(unit)
    return unit


@units_router.delete("/{unit_id}", status_code=204)
def delete_unit(unit_id: uuid.UUID, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    # Null out unit_id FK on objects before deleting (no DB-level cascade)
    db.query(Object).filter(Object.unit_id == unit_id).update(
        {Object.unit_id: None}, synchronize_session=False
    )
    db.delete(unit)
    db.commit()
