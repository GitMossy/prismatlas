"""
WorkCalendar and CalendarException — FR-4.4.2 Calendar-Aware CPM

A WorkCalendar defines which days are working days and carries a list of
exceptions (public holidays, shutdowns, etc.).  The CPM engine uses the
calendar to convert duration_days (float) into actual calendar dates.

Default calendar: Mon–Fri working, Sat–Sun non-working, no exceptions.
"""
import uuid
from datetime import date
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class WorkCalendar(UUIDMixin, TimestampMixin, Base):
    """
    A named work calendar attached to a project (or shared across projects when
    project_id is NULL).

    working_days: list of ISO weekday numbers that are working days.
                  [1, 2, 3, 4, 5] = Mon–Fri (default)
                  [1, 2, 3, 4, 5, 6] = Mon–Sat
    hours_per_day: hours in a working day (default 8.0).  Used to convert
                   effort_hours → duration_days.
    """
    __tablename__ = "work_calendars"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # ISO weekday numbers (1=Mon … 7=Sun) that count as working days
    working_days: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=lambda: [1, 2, 3, 4, 5]
    )
    hours_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=8.0)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    project: Mapped["Project | None"] = relationship("Project")
    exceptions: Mapped[list["CalendarException"]] = relationship(
        "CalendarException", back_populates="calendar", cascade="all, delete-orphan"
    )


class CalendarException(UUIDMixin, Base):
    """
    A single-day exception on a WorkCalendar (e.g. a public holiday or
    an unplanned shutdown).  exception_date is excluded from working days
    regardless of its weekday.
    """
    __tablename__ = "calendar_exceptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_calendars.id", ondelete="CASCADE"), nullable=False
    )
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))   # e.g. "Christmas Day"
    is_working: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # False = non-working (holiday), True = working override (e.g. mandatory Saturday)

    calendar: Mapped["WorkCalendar"] = relationship("WorkCalendar", back_populates="exceptions")
