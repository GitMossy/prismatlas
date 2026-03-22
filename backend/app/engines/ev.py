"""
Earned Value engine — FR-4.4.5.

Computes PV, EV, and SPI for a baseline at a given day offset.

Definitions:
  PV (Planned Value)   = sum of planned_effort_hours for tasks whose planned_finish <= as_of_day
  EV (Earned Value)    = sum of planned_effort_hours for tasks that are complete AND
                         whose planned_finish <= as_of_day
  SPI (Schedule Perf.) = EV / PV  (None when PV == 0)

All date comparisons use integer day-offsets from the project anchor date,
consistent with the CPM engine and TaskInstance date fields.
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.baseline import Baseline, BaselineTask
from app.models.workflow import TaskInstance


def compute_ev(baseline_id: uuid.UUID, as_of_day: int, db: Session) -> dict[str, Any]:
    """
    Compute Earned Value metrics for a baseline as of a given day offset.

    Args:
        baseline_id: UUID of the Baseline row.
        as_of_day:   Integer day offset from project start (e.g. 30 = 30 days in).
        db:          SQLAlchemy session.

    Returns:
        {
            "pv": float,
            "ev": float,
            "spi": float | None,
            "task_count_total": int,
            "task_count_complete": int,
        }
    """
    baseline = db.query(Baseline).filter(Baseline.id == baseline_id).first()
    if not baseline:
        return {"pv": 0.0, "ev": 0.0, "spi": None, "task_count_total": 0, "task_count_complete": 0}

    # Load all baseline tasks with their planned_finish and planned_effort_hours
    b_tasks = (
        db.query(BaselineTask)
        .filter(BaselineTask.baseline_id == baseline_id)
        .all()
    )

    if not b_tasks:
        return {"pv": 0.0, "ev": 0.0, "spi": None, "task_count_total": 0, "task_count_complete": 0}

    # Build lookup: task_instance_id → status
    task_ids = [bt.task_instance_id for bt in b_tasks]
    live_tasks = db.query(TaskInstance).filter(TaskInstance.id.in_(task_ids)).all()
    status_map: dict[uuid.UUID, str] = {t.id: t.status for t in live_tasks}

    pv = 0.0
    ev = 0.0
    task_count_total = len(b_tasks)
    task_count_complete = 0

    for bt in b_tasks:
        hours = bt.planned_effort_hours or 0.0
        finish = bt.planned_finish

        # A task contributes to PV if its planned finish is on or before as_of_day
        if finish is not None and finish <= as_of_day:
            pv += hours

            live_status = status_map.get(bt.task_instance_id)
            if live_status == "complete":
                ev += hours
                task_count_complete += 1

    spi = (ev / pv) if pv > 0 else None

    return {
        "pv": round(pv, 4),
        "ev": round(ev, 4),
        "spi": round(spi, 4) if spi is not None else None,
        "task_count_total": task_count_total,
        "task_count_complete": task_count_complete,
    }
