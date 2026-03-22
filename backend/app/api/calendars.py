"""
Work Calendar API — FR-4.4.2 Calendar-Aware CPM

CRUD for WorkCalendar and CalendarException.
Calendars are used by the CPM engine to convert day-offset durations
into actual calendar dates, skipping non-working days and exceptions.
"""
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.calendar import WorkCalendar, CalendarException

router = APIRouter(prefix="/calendars", tags=["calendars"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CalendarExceptionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    calendar_id: uuid.UUID
    exception_date: date
    name: str | None
    is_working: bool


class WorkCalendarCreate(BaseModel):
    project_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    working_days: list[int] = [1, 2, 3, 4, 5]  # Mon–Fri
    hours_per_day: float = 8.0
    is_default: bool = False


class WorkCalendarUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    working_days: list[int] | None = None
    hours_per_day: float | None = None
    is_default: bool | None = None


class WorkCalendarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    name: str
    description: str | None
    working_days: list[Any]
    hours_per_day: float
    is_default: bool
    exceptions: list[CalendarExceptionSchema]


class CalendarExceptionCreate(BaseModel):
    exception_date: date
    name: str | None = None
    is_working: bool = False  # False = holiday (non-working)


# ── Calendar endpoints ────────────────────────────────────────────────────────

@router.get("", response_model=list[WorkCalendarResponse])
def list_calendars(
    project_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(WorkCalendar)
    if project_id:
        q = q.filter(
            (WorkCalendar.project_id == project_id) | (WorkCalendar.project_id.is_(None))
        )
    return q.all()


@router.post("", response_model=WorkCalendarResponse, status_code=201)
def create_calendar(body: WorkCalendarCreate, db: Session = Depends(get_db)):
    if body.is_default and body.project_id:
        # Unset any existing default for this project
        db.query(WorkCalendar).filter(
            WorkCalendar.project_id == body.project_id,
            WorkCalendar.is_default == True,  # noqa: E712
        ).update({"is_default": False})
    calendar = WorkCalendar(**body.model_dump())
    db.add(calendar)
    db.commit()
    db.refresh(calendar)
    return calendar


@router.get("/{calendar_id}", response_model=WorkCalendarResponse)
def get_calendar(calendar_id: uuid.UUID, db: Session = Depends(get_db)):
    cal = db.query(WorkCalendar).filter(WorkCalendar.id == calendar_id).first()
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return cal


@router.patch("/{calendar_id}", response_model=WorkCalendarResponse)
def update_calendar(
    calendar_id: uuid.UUID, body: WorkCalendarUpdate, db: Session = Depends(get_db)
):
    cal = db.query(WorkCalendar).filter(WorkCalendar.id == calendar_id).first()
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cal, field, value)
    db.commit()
    db.refresh(cal)
    return cal


@router.delete("/{calendar_id}", status_code=204)
def delete_calendar(calendar_id: uuid.UUID, db: Session = Depends(get_db)):
    cal = db.query(WorkCalendar).filter(WorkCalendar.id == calendar_id).first()
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")
    db.delete(cal)
    db.commit()


# ── Exception sub-resource ────────────────────────────────────────────────────

@router.post(
    "/{calendar_id}/exceptions",
    response_model=CalendarExceptionSchema,
    status_code=201,
)
def add_exception(
    calendar_id: uuid.UUID,
    body: CalendarExceptionCreate,
    db: Session = Depends(get_db),
):
    cal = db.query(WorkCalendar).filter(WorkCalendar.id == calendar_id).first()
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")
    exc = CalendarException(calendar_id=calendar_id, **body.model_dump())
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc


@router.delete("/{calendar_id}/exceptions/{exception_id}", status_code=204)
def remove_exception(
    calendar_id: uuid.UUID,
    exception_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    exc = (
        db.query(CalendarException)
        .filter(
            CalendarException.id == exception_id,
            CalendarException.calendar_id == calendar_id,
        )
        .first()
    )
    if not exc:
        raise HTTPException(status_code=404, detail="Calendar exception not found")
    db.delete(exc)
    db.commit()
