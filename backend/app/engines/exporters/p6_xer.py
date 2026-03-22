"""
Primavera P6 XER export — maps PrismAtlas entities to P6 data structures.

Mapping:
- WorkflowInstance → P6 PROJECT
- TaskInstance → P6 TASK
- DependencyRule (with both entity IDs) → P6 TASKPRED
- Resource → P6 RSRC
- CPM day offsets → calendar dates via project.planned_start as day-0 anchor
"""
from datetime import date, timedelta
import uuid

from sqlalchemy.orm import Session

from app.models.workflow import WorkflowInstance, StageInstance, TaskInstance
from app.models.dependency import DependencyRule
from app.models.resource import Resource
from app.models.project import Project


def export_project_xer(project_id: uuid.UUID, db: Session) -> str:
    """Generate P6 XER file content as string.

    XER format is tab-delimited:
      %T  <TABLE_NAME>
      %F  <field1>  <field2>  ...
      %R  <val1>    <val2>    ...
      %E  (end of table)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return ""

    anchor = date.today()  # day-0 anchor; use planned_start if available

    instances = (
        db.query(WorkflowInstance)
        .filter(WorkflowInstance.entity_type == "object")
        .all()
    )

    lines: list[str] = []
    lines.append("ERMHDR\t18.8\t2023-01-01\tProject\tadmin\t\t\t\t")

    # ── %T PROJECT ────────────────────────────────────────────────────────────
    lines.append("%T\tPROJECT")
    lines.append("%F\tproj_id\tproj_short_name\tproj_name\tplan_start_date\tstatus_code")
    for inst in instances:
        lines.append(
            "%R\t{proj_id}\t{short}\t{name}\t{start}\tIN_PROGRESS".format(
                proj_id=str(inst.id)[:8],
                short=str(inst.id)[:8],
                name=f"WI_{str(inst.id)[:8]}",
                start=anchor.strftime("%Y-%m-%d 00:00"),
            )
        )
    lines.append("%E")

    # ── %T RSRC ───────────────────────────────────────────────────────────────
    resources = db.query(Resource).filter(Resource.project_id == project_id).all()
    lines.append("%T\tRSRC")
    lines.append("%F\trsrc_id\trsrc_name\trsrc_type\tmax_qty_per_hr")
    for res in resources:
        lines.append(
            "%R\t{rid}\t{name}\tRT_Labor\t{cap}".format(
                rid=str(res.id)[:8],
                name=res.name,
                cap=round((res.capacity_hours_per_day or 8.0) / 8.0, 4),
            )
        )
    lines.append("%E")

    # ── %T TASK ───────────────────────────────────────────────────────────────
    lines.append("%T\tTASK")
    lines.append(
        "%F\ttask_id\tproj_id\ttask_code\ttask_name\t"
        "target_drtn_hr_cnt\ttarget_work_qty\tearly_start_date\tearly_end_date\t"
        "status_code"
    )
    task_map: dict[uuid.UUID, str] = {}  # task_id → p6 task_code
    for inst in instances:
        for stage in sorted(inst.stage_instances, key=lambda s: s.stage_order):
            for task in sorted(stage.task_instances, key=lambda t: t.task_order):
                code = f"T{str(task.id)[:7]}"
                task_map[task.id] = code
                duration_hr = (task.duration_days or 1) * 8
                effort_hr = task.effort_hours or duration_hr
                es = _format_xer_date(task.early_start or 0, anchor)
                ef = _format_xer_date(task.early_finish or (task.early_start or 0) + (task.duration_days or 1), anchor)
                status = "TK_Complete" if task.status == "complete" else "TK_NotStart"
                lines.append(
                    "%R\t{code}\t{proj}\t{code}\t{name}\t{dur}\t{eff}\t{es}\t{ef}\t{st}".format(
                        code=code,
                        proj=str(inst.id)[:8],
                        name=task.task_name[:40],
                        dur=duration_hr,
                        eff=effort_hr,
                        es=es,
                        ef=ef,
                        st=status,
                    )
                )
    lines.append("%E")

    # ── %T TASKPRED ───────────────────────────────────────────────────────────
    # Map DependencyRules where both source and target task IDs are known.
    # PrismAtlas DependencyRules connect entities, not tasks directly;
    # we emit TASKPRED rows only for rules whose source and target IDs can be
    # resolved to TaskInstance IDs within this export.
    lines.append("%T\tTASKPRED")
    lines.append("%F\tpred_task_id\ttask_id\tpred_type\tlag_hr_cnt")
    rules = (
        db.query(DependencyRule)
        .filter(
            DependencyRule.source_entity_id.isnot(None),
            DependencyRule.target_entity_id.isnot(None),
        )
        .all()
    )
    for rule in rules:
        src_code = task_map.get(rule.source_entity_id)
        tgt_code = task_map.get(rule.target_entity_id)
        if src_code and tgt_code:
            # Map PrismAtlas link_type to P6 predecessor type codes
            link_map = {"FS": "PR_FS", "SS": "PR_SS", "FF": "PR_FF", "SF": "PR_SF"}
            link = link_map.get(rule.link_type or "FS", "PR_FS")
            lag_hr = (rule.lag_days or 0) * 8
            lines.append(f"%R\t{src_code}\t{tgt_code}\t{link}\t{lag_hr}")
    lines.append("%E")

    return "\n".join(lines)


def _format_xer_date(day_offset: int, anchor: date) -> str:
    """Convert day offset to XER date format: YYYY-MM-DD HH:MM"""
    d = anchor + timedelta(days=day_offset)
    return d.strftime("%Y-%m-%d 00:00")
