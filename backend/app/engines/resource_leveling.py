"""
Resource leveling engine — FR-4.4.4

List-scheduling heuristic:
1. Sort non-critical tasks by total_float ascending (least float first, i.e.
   most constrained tasks have priority in keeping their original dates).
2. For each resource, build a daily load profile.
3. Identify over-allocated days (load > capacity).
4. Shift tasks within their total_float window to resolve over-allocation.
5. Return proposed schedule without persisting — user confirms separately via
   POST /workflow-instances/{id}/schedule/level/confirm.

Assumptions:
- Effort is distributed uniformly across task duration.
- Tasks cannot be split (non-preemptive scheduling).
- Only tasks with assigned_resource_id and effort_hours are considered.
- CPM must have been run first (early_start, total_float must be populated).
"""
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.workflow import WorkflowInstance, TaskInstance
from app.models.resource import Resource


@dataclass
class DailyLoad:
    resource_id: uuid.UUID
    day: int
    effort_hours: float


def compute_resource_loading(workflow_instance_id: uuid.UUID, db: Session) -> list[dict]:
    """
    Per-resource, per-day load data.

    Returns list of:
      {resource_id, resource_name, day, effort_hours, capacity_hours, utilization_pct}

    Assumes uniform effort distribution across task duration.
    CPM must have been run so that early_start is populated.
    """
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == workflow_instance_id).first()
    if not instance:
        return []

    resource_loading: dict[uuid.UUID, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    resources: dict[uuid.UUID, Resource] = {}

    for stage in instance.stage_instances:
        for task in stage.task_instances:
            if task.assigned_resource_id and task.early_start is not None and task.effort_hours:
                res_id = task.assigned_resource_id
                duration = task.duration_days or 1
                daily_effort = task.effort_hours / duration
                for day in range(task.early_start, task.early_start + duration):
                    resource_loading[res_id][day] += daily_effort
                if res_id not in resources:
                    res = db.query(Resource).filter(Resource.id == res_id).first()
                    if res:
                        resources[res_id] = res

    result: list[dict] = []
    for res_id, daily_loads in resource_loading.items():
        res = resources.get(res_id)
        cap = (res.capacity_hours_per_day or 8.0) if res else 8.0
        for day, effort in sorted(daily_loads.items()):
            result.append({
                "resource_id": str(res_id),
                "resource_name": res.name if res else "Unknown",
                "day": day,
                "effort_hours": round(effort, 2),
                "capacity_hours": cap,
                "utilization_pct": round(effort / cap * 100, 1) if cap > 0 else 0,
            })
    return result


def level_resources(workflow_instance_id: uuid.UUID, db: Session) -> dict:
    """
    Propose a leveled schedule using a list-scheduling heuristic.

    Algorithm:
    1. Run CPM (or use existing CPM results if already computed).
    2. Collect all tasks that have: assigned_resource_id, effort_hours, early_start, total_float.
    3. Sort tasks by total_float ascending (most constrained first).
    4. For each resource, maintain a daily load dict.
    5. For each task in priority order, try to schedule it at its early_start.
       If the resource is over-allocated on any day in [start, start+duration),
       shift the task forward by one day at a time until the resource fits OR
       we exhaust the float window (late_start).
    6. Record proposed start adjustments without writing to DB.

    Returns:
      {
        "leveled_tasks": [{task_id, original_start, proposed_start, shift_days}],
        "over_allocated_resolved": int,
        "over_allocated_remaining": int,
      }
    """
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == workflow_instance_id).first()
    if not instance:
        return {"leveled_tasks": [], "over_allocated_resolved": 0, "over_allocated_remaining": 0}

    # Collect candidate tasks
    candidate_tasks: list[TaskInstance] = []
    for stage in instance.stage_instances:
        for task in stage.task_instances:
            if (
                task.assigned_resource_id is not None
                and task.effort_hours
                and task.early_start is not None
                and task.total_float is not None
                and not task.is_critical  # Don't shift critical tasks
            ):
                candidate_tasks.append(task)

    # Sort by total_float ascending (least float = highest priority)
    candidate_tasks.sort(key=lambda t: t.total_float or 0)

    # Build initial resource daily load from ALL tasks (including critical ones)
    resource_load: dict[uuid.UUID, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    resource_capacity: dict[uuid.UUID, float] = {}

    for stage in instance.stage_instances:
        for task in stage.task_instances:
            if task.assigned_resource_id and task.early_start is not None and task.effort_hours:
                res_id = task.assigned_resource_id
                duration = task.duration_days or 1
                daily_effort = task.effort_hours / duration
                for day in range(task.early_start, task.early_start + duration):
                    resource_load[res_id][day] += daily_effort

    # Load resource capacities
    all_resource_ids = {t.assigned_resource_id for t in candidate_tasks if t.assigned_resource_id}
    for res_id in all_resource_ids:
        res = db.query(Resource).filter(Resource.id == res_id).first()
        resource_capacity[res_id] = res.capacity_hours_per_day if res else 8.0

    leveled_tasks: list[dict[str, Any]] = []
    resolved = 0
    remaining = 0

    for task in candidate_tasks:
        res_id = task.assigned_resource_id
        capacity = resource_capacity.get(res_id, 8.0)
        duration = task.duration_days or 1
        daily_effort = task.effort_hours / duration
        original_start = task.early_start
        late_start = task.late_start if task.late_start is not None else original_start

        # Remove task's contribution from load before re-scheduling
        for day in range(original_start, original_start + duration):
            resource_load[res_id][day] -= daily_effort

        # Try to find a slot within float window
        best_start = original_start
        placed = False
        for proposed_start in range(original_start, late_start + 1):
            fits = all(
                resource_load[res_id][day] + daily_effort <= capacity + 1e-9
                for day in range(proposed_start, proposed_start + duration)
            )
            if fits:
                best_start = proposed_start
                placed = True
                break

        # Add task back at best_start
        for day in range(best_start, best_start + duration):
            resource_load[res_id][day] += daily_effort

        shift = best_start - original_start
        if shift > 0 or not placed:
            leveled_tasks.append({
                "task_id": str(task.id),
                "task_name": task.task_name,
                "original_start": original_start,
                "proposed_start": best_start,
                "shift_days": shift,
                "leveled": placed,
            })
            if placed:
                resolved += 1
            else:
                remaining += 1

    return {
        "leveled_tasks": leveled_tasks,
        "over_allocated_resolved": resolved,
        "over_allocated_remaining": remaining,
    }
