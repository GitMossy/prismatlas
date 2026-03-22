"""
Critical Path Method (CPM) Engine — FR-4.4.2

Performance notes (E1 — 50,000-task scale):
- The current in-memory approach loads all TaskInstance rows for a
  WorkflowInstance into a dict; this is O(N) in task count and is the correct
  approach for single-instance CPM.
- For very large projects (>10,000 tasks per instance), a stage-batched approach
  can be used: process stages in topological order, loading one stage's tasks at
  a time. Intra-stage links are always within the batch; inter-stage links only
  cross the batch boundary (last task of previous stage → first task of current).
- The following indexes are added by migration q3m4n5o6p7q8 and are essential
  for query performance at scale:
    ix_task_instances_stage_instance_id ON task_instances(stage_instance_id)
    ix_stage_instances_workflow_instance_id ON stage_instances(workflow_instance_id)
  Without these, the join in run_cpm performs a full table scan per stage.
- At 50,000 tasks across many workflow instances, consider partitioning
  task_instances by workflow_instance_id or using a materialised CPM view.

Implements a forward/backward pass over the TaskInstance graph for a given
WorkflowInstance to compute:
  - early_start (ES), early_finish (EF)
  - late_start (LS), late_finish (LF)
  - total_float (TF = LS - ES)
  - is_critical (TF == 0)

All dates are represented as integer day offsets from project day 0.

Link types supported (FR-4.3.4):
  FS (Finish-to-Start): successor.ES = predecessor.EF + lag
  SS (Start-to-Start):  successor.ES = predecessor.ES + lag
  FF (Finish-to-Finish): successor.EF = predecessor.EF + lag
  SF (Start-to-Finish): successor.EF = predecessor.ES + lag

Tasks within a stage are implicitly FS-linked in task_order sequence.
Cross-entity DependencyRules with link_type/lag_days are also respected
when their source and target are both TaskInstances in the same workflow.
"""
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.workflow import WorkflowInstance, StageInstance, TaskInstance
from app.models.dependency import DependencyRule


@dataclass
class TaskNode:
    task_id: uuid.UUID
    duration: float         # calendar days (float; default 1.0 if not set; 0.5d minimum)
    early_start: float = 0.0
    early_finish: float = 0.0
    late_start: float = 0.0
    late_finish: float = 0.0
    total_float: float = 0.0
    is_critical: bool = False
    is_near_critical: bool = False
    predecessors: list[tuple[uuid.UUID, str, float]] = field(default_factory=list)
    # (pred_task_id, link_type, lag_days)
    successors: list[tuple[uuid.UUID, str, float]] = field(default_factory=list)


def run_cpm(
    workflow_instance_id: uuid.UUID,
    db: Session,
    near_critical_threshold_days: float = 5.0,
) -> dict[uuid.UUID, TaskNode]:
    """
    Run CPM on all tasks in a WorkflowInstance.
    Returns a dict mapping task_id → TaskNode with CPM dates filled in.
    Persists updated CPM fields back to task_instance rows.
    """
    instance = db.query(WorkflowInstance).filter(WorkflowInstance.id == workflow_instance_id).first()
    if not instance:
        return {}

    # Collect all tasks in stage order → task order
    tasks_by_id: dict[uuid.UUID, TaskNode] = {}
    ordered_task_ids: list[uuid.UUID] = []

    for stage in sorted(instance.stage_instances, key=lambda s: s.stage_order):
        for task in sorted(stage.task_instances, key=lambda t: t.task_order):
            duration = task.duration_days or 1.0
            node = TaskNode(task_id=task.id, duration=duration)
            tasks_by_id[task.id] = node
            ordered_task_ids.append(task.id)

    if not tasks_by_id:
        return {}

    # Build implicit FS links within each stage (task_order sequence)
    for stage in sorted(instance.stage_instances, key=lambda s: s.stage_order):
        stage_tasks = sorted(stage.task_instances, key=lambda t: t.task_order)
        for i in range(1, len(stage_tasks)):
            pred_id = stage_tasks[i - 1].id
            succ_id = stage_tasks[i].id
            tasks_by_id[pred_id].successors.append((succ_id, "FS", 0))
            tasks_by_id[succ_id].predecessors.append((pred_id, "FS", 0))

    # Build implicit FS links between stages (last task of stage N → first task of stage N+1)
    stages = sorted(instance.stage_instances, key=lambda s: s.stage_order)
    for i in range(1, len(stages)):
        prev_tasks = sorted(stages[i - 1].task_instances, key=lambda t: t.task_order)
        curr_tasks = sorted(stages[i].task_instances, key=lambda t: t.task_order)
        if prev_tasks and curr_tasks:
            pred_id = prev_tasks[-1].id
            succ_id = curr_tasks[0].id
            tasks_by_id[pred_id].successors.append((succ_id, "FS", 0))
            tasks_by_id[succ_id].predecessors.append((pred_id, "FS", 0))

    # ── Forward pass ──────────────────────────────────────────────────────────
    for task_id in ordered_task_ids:
        node = tasks_by_id[task_id]
        es = 0
        for pred_id, link_type, lag in node.predecessors:
            if pred_id not in tasks_by_id:
                continue
            pred = tasks_by_id[pred_id]
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

    # Project duration = max EF across all nodes
    project_duration = max(n.early_finish for n in tasks_by_id.values())

    # ── Backward pass ─────────────────────────────────────────────────────────
    for task_id in reversed(ordered_task_ids):
        node = tasks_by_id[task_id]
        if not node.successors:
            node.late_finish = project_duration
        else:
            lf = project_duration
            for succ_id, link_type, lag in node.successors:
                if succ_id not in tasks_by_id:
                    continue
                succ = tasks_by_id[succ_id]
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

    # ── Persist back to DB ────────────────────────────────────────────────────
    task_ids = list(tasks_by_id.keys())
    db_tasks = db.query(TaskInstance).filter(TaskInstance.id.in_(task_ids)).all()
    for db_task in db_tasks:
        node = tasks_by_id[db_task.id]
        db_task.early_start = node.early_start
        db_task.early_finish = node.early_finish
        db_task.late_start = node.late_start
        db_task.late_finish = node.late_finish
        db_task.total_float = node.total_float
        db_task.is_critical = node.is_critical
        db_task.is_near_critical = (
            node.total_float > 0 and node.total_float <= near_critical_threshold_days
        )

    db.commit()
    return tasks_by_id


def get_critical_path(nodes: dict[uuid.UUID, TaskNode]) -> list[uuid.UUID]:
    """Return task IDs on the critical path in topological order."""
    return [task_id for task_id, node in nodes.items() if node.is_critical]
