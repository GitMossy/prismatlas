"""
What-if scenario engine — FR-4.4.6.

Loads a baseline, applies per-task overrides from a scenario, then runs CPM
entirely in-memory. Results are NEVER written back to task_instances.

Returns the same TaskNode structure as the main CPM engine so callers can
reuse comparison logic.
"""
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.engines.cpm import TaskNode
from app.models.baseline import Baseline, BaselineTask
from app.models.scenario import Scenario, ScenarioTaskOverride
from app.models.workflow import TaskInstance


def compute_scenario_cpm(scenario_id: uuid.UUID, db: Session) -> dict[str, Any]:
    """
    Load a scenario and its baseline, apply overrides, run CPM in-memory.

    Returns a dict with:
      {
        "scenario_id": str,
        "project_duration": int,           # max EF across all tasks
        "tasks": {
            "<task_id>": {
                "early_start": int,
                "early_finish": int,
                "late_start": int,
                "late_finish": int,
                "total_float": int,
                "is_critical": bool,
                "duration_days": int,
                "effort_hours": float | None,
            }
        }
      }

    Returns an empty dict structure if the scenario or baseline is not found.
    """
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        return {"error": "Scenario not found"}

    if not scenario.source_baseline_id:
        return {"error": "Scenario has no source_baseline_id; cannot compute CPM"}

    baseline = db.query(Baseline).filter(Baseline.id == scenario.source_baseline_id).first()
    if not baseline:
        return {"error": "Source baseline not found"}

    # Load baseline tasks
    b_tasks = (
        db.query(BaselineTask)
        .filter(BaselineTask.baseline_id == baseline.id)
        .all()
    )
    if not b_tasks:
        return {"scenario_id": str(scenario_id), "project_duration": 0, "tasks": {}}

    # Build override lookup
    overrides: dict[uuid.UUID, ScenarioTaskOverride] = {
        o.task_instance_id: o
        for o in db.query(ScenarioTaskOverride).filter(
            ScenarioTaskOverride.scenario_id == scenario_id
        ).all()
    }

    # Load live task instances for ordering (stage_order, task_order)
    task_ids = [bt.task_instance_id for bt in b_tasks]
    live_tasks = db.query(TaskInstance).filter(TaskInstance.id.in_(task_ids)).all()
    live_map: dict[uuid.UUID, TaskInstance] = {t.id: t for t in live_tasks}

    # Sort by (stage_order, task_order) using live task data
    def _sort_key(bt: BaselineTask):
        task = live_map.get(bt.task_instance_id)
        if task and task.stage_instance:
            return (task.stage_instance.stage_order, task.task_order)
        return (9999, 9999)

    sorted_b_tasks = sorted(b_tasks, key=_sort_key)

    # Build TaskNode graph
    nodes: dict[uuid.UUID, TaskNode] = {}
    ordered_ids: list[uuid.UUID] = []

    for bt in sorted_b_tasks:
        task_id = bt.task_instance_id
        override = overrides.get(task_id)

        # Duration: override wins, then baseline planned_finish - planned_start, else 1
        if override and override.duration_days is not None:
            duration = override.duration_days
        elif bt.planned_start is not None and bt.planned_finish is not None:
            duration = max(1, bt.planned_finish - bt.planned_start)
        else:
            duration = 1

        effort = None
        if override and override.effort_hours is not None:
            effort = override.effort_hours
        elif bt.planned_effort_hours is not None:
            effort = bt.planned_effort_hours

        node = TaskNode(task_id=task_id, duration=duration)
        # Stash effort for result output (TaskNode doesn't carry it, so we track separately)
        nodes[task_id] = node
        ordered_ids.append(task_id)

    effort_map: dict[uuid.UUID, float | None] = {}
    for bt in sorted_b_tasks:
        task_id = bt.task_instance_id
        override = overrides.get(task_id)
        if override and override.effort_hours is not None:
            effort_map[task_id] = override.effort_hours
        else:
            effort_map[task_id] = bt.planned_effort_hours

    # Build implicit FS links between consecutive tasks in the ordered list
    # (same logic as main CPM: within-stage FS by task_order)
    _build_implicit_links(sorted_b_tasks, live_map, nodes)

    # Apply start_offset_days overrides by shifting the ES constraint
    for task_id, override in overrides.items():
        if override.start_offset_days is not None and task_id in nodes:
            node = nodes[task_id]
            # Force early_start minimum via a phantom predecessor with no duration
            # We implement this as a pre-set minimum ES that the forward pass respects
            node.early_start = max(node.early_start, override.start_offset_days)
            node.early_finish = node.early_start + node.duration

    # ── Forward pass ──────────────────────────────────────────────────────────
    for task_id in ordered_ids:
        node = nodes[task_id]
        es = node.early_start  # may already have start_offset applied
        for pred_id, link_type, lag in node.predecessors:
            if pred_id not in nodes:
                continue
            pred = nodes[pred_id]
            if link_type == "FS":
                candidate = pred.early_finish + lag
            elif link_type == "SS":
                candidate = pred.early_start + lag
            elif link_type == "FF":
                candidate = pred.early_finish + lag - node.duration
            elif link_type == "SF":
                candidate = pred.early_start + lag - node.duration
            else:
                candidate = pred.early_finish + lag
            es = max(es, candidate)
        node.early_start = max(0, es)
        node.early_finish = node.early_start + node.duration

    # ── Backward pass ─────────────────────────────────────────────────────────
    project_duration = max((n.early_finish for n in nodes.values()), default=0)

    for task_id in reversed(ordered_ids):
        node = nodes[task_id]
        if not node.successors:
            node.late_finish = project_duration
        else:
            lf = project_duration
            for succ_id, link_type, lag in node.successors:
                if succ_id not in nodes:
                    continue
                succ = nodes[succ_id]
                if link_type == "FS":
                    candidate = succ.late_start - lag
                elif link_type == "SS":
                    candidate = succ.late_start - lag + node.duration
                elif link_type == "FF":
                    candidate = succ.late_finish - lag
                elif link_type == "SF":
                    candidate = succ.late_finish - lag + node.duration
                else:
                    candidate = succ.late_start - lag
                lf = min(lf, candidate)
            node.late_finish = lf
        node.late_start = node.late_finish - node.duration
        node.total_float = node.late_start - node.early_start
        node.is_critical = node.total_float == 0

    # ── Build result (no DB writes) ────────────────────────────────────────────
    tasks_out: dict[str, Any] = {}
    for task_id, node in nodes.items():
        tasks_out[str(task_id)] = {
            "early_start": node.early_start,
            "early_finish": node.early_finish,
            "late_start": node.late_start,
            "late_finish": node.late_finish,
            "total_float": node.total_float,
            "is_critical": node.is_critical,
            "duration_days": node.duration,
            "effort_hours": effort_map.get(task_id),
        }

    return {
        "scenario_id": str(scenario_id),
        "project_duration": project_duration,
        "tasks": tasks_out,
    }


def _build_implicit_links(
    sorted_b_tasks: list,
    live_map: dict[uuid.UUID, "TaskInstance"],
    nodes: dict[uuid.UUID, TaskNode],
) -> None:
    """
    Reproduce the same implicit FS links the main CPM uses:
    - Within a stage: task[i-1] → task[i] (FS)
    - Between stages: last task of stage N → first task of stage N+1 (FS)
    """
    # Group by stage_order
    from collections import defaultdict
    stages: dict[int, list[uuid.UUID]] = defaultdict(list)

    for bt in sorted_b_tasks:
        task = live_map.get(bt.task_instance_id)
        if task and task.stage_instance:
            stages[task.stage_instance.stage_order].append(bt.task_instance_id)

    stage_orders = sorted(stages.keys())

    for stage_order in stage_orders:
        task_ids_in_stage = stages[stage_order]
        for i in range(1, len(task_ids_in_stage)):
            pred_id = task_ids_in_stage[i - 1]
            succ_id = task_ids_in_stage[i]
            if pred_id in nodes and succ_id in nodes:
                nodes[pred_id].successors.append((succ_id, "FS", 0))
                nodes[succ_id].predecessors.append((pred_id, "FS", 0))

    for i in range(1, len(stage_orders)):
        prev_tasks = stages[stage_orders[i - 1]]
        curr_tasks = stages[stage_orders[i]]
        if prev_tasks and curr_tasks:
            pred_id = prev_tasks[-1]
            succ_id = curr_tasks[0]
            if pred_id in nodes and succ_id in nodes:
                nodes[pred_id].successors.append((succ_id, "FS", 0))
                nodes[succ_id].predecessors.append((pred_id, "FS", 0))
