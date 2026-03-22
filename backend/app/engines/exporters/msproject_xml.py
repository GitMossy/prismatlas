"""
Microsoft Project XML export.
Maps WorkflowInstance tasks to MSProject XML format.
Uses xml.etree.ElementTree (stdlib, no extra deps).

MS Project XML spec reference: Microsoft Office Project 2007 XML Data Interchange Schema.
Key elements:
  Project → Tasks → Task (each TaskInstance)
  Project → Resources → Resource (each Resource)
  Project → Assignments → Assignment (task ↔ resource links)
"""
import uuid
from datetime import date, timedelta
from sqlalchemy.orm import Session
import xml.etree.ElementTree as ET

from app.models.workflow import WorkflowInstance, StageInstance, TaskInstance
from app.models.resource import Resource
from app.models.project import Project


# MS Project UID starts at 0 (summary task) — use incremental integers.
_TASK_UID_START = 1
_RES_UID_START = 1


def export_project_xml(project_id: uuid.UUID, db: Session) -> str:
    """Generate MS Project XML string."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return '<?xml version="1.0" encoding="UTF-8"?><Project/>'

    anchor = date.today()  # day-0 anchor

    root = ET.Element("Project", xmlns="http://schemas.microsoft.com/project")

    _sub(root, "Name", project.name)
    _sub(root, "Title", project.name)
    _sub(root, "StartDate", _ms_date(0, anchor))
    _sub(root, "CalendarUID", "1")

    # ── Calendars ─────────────────────────────────────────────────────────────
    calendars_el = ET.SubElement(root, "Calendars")
    cal = ET.SubElement(calendars_el, "Calendar")
    _sub(cal, "UID", "1")
    _sub(cal, "Name", "Standard")
    _sub(cal, "IsBaseCalendar", "1")

    # ── Tasks ─────────────────────────────────────────────────────────────────
    instances = (
        db.query(WorkflowInstance)
        .filter(WorkflowInstance.entity_type == "object")
        .all()
    )

    tasks_el = ET.SubElement(root, "Tasks")
    resources_el = ET.SubElement(root, "Resources")
    assignments_el = ET.SubElement(root, "Assignments")

    uid_counter = _TASK_UID_START
    task_uid_map: dict[uuid.UUID, int] = {}  # task_id → MS Project UID

    for inst in instances:
        # Summary task for the WorkflowInstance
        summary = ET.SubElement(tasks_el, "Task")
        _sub(summary, "UID", str(uid_counter))
        _sub(summary, "ID", str(uid_counter))
        _sub(summary, "Name", f"Workflow {str(inst.id)[:8]}")
        _sub(summary, "Summary", "1")
        _sub(summary, "OutlineLevel", "1")
        uid_counter += 1

        for stage in sorted(inst.stage_instances, key=lambda s: s.stage_order):
            # Stage summary task
            stage_task = ET.SubElement(tasks_el, "Task")
            _sub(stage_task, "UID", str(uid_counter))
            _sub(stage_task, "ID", str(uid_counter))
            _sub(stage_task, "Name", stage.stage_name)
            _sub(stage_task, "Summary", "1")
            _sub(stage_task, "OutlineLevel", "2")
            uid_counter += 1

            for task in sorted(stage.task_instances, key=lambda t: t.task_order):
                t_el = ET.SubElement(tasks_el, "Task")
                _sub(t_el, "UID", str(uid_counter))
                _sub(t_el, "ID", str(uid_counter))
                _sub(t_el, "Name", task.task_name)
                _sub(t_el, "OutlineLevel", "3")

                dur_days = task.duration_days or 1
                _sub(t_el, "Duration", f"PT{dur_days * 8}H0M0S")
                _sub(t_el, "Work", f"PT{int(task.effort_hours or dur_days * 8)}H0M0S")

                es = task.early_start or 0
                ef = task.early_finish or (es + dur_days)
                _sub(t_el, "Start", _ms_date(es, anchor))
                _sub(t_el, "Finish", _ms_date(ef, anchor))

                status_pct = "100" if task.status == "complete" else "0"
                _sub(t_el, "PercentComplete", status_pct)

                task_uid_map[task.id] = uid_counter
                uid_counter += 1

    # ── Resources ─────────────────────────────────────────────────────────────
    resources = db.query(Resource).filter(Resource.project_id == project_id).all()
    res_uid_map: dict[uuid.UUID, int] = {}
    for i, res in enumerate(resources, start=_RES_UID_START):
        r_el = ET.SubElement(resources_el, "Resource")
        _sub(r_el, "UID", str(i))
        _sub(r_el, "ID", str(i))
        _sub(r_el, "Name", res.name)
        _sub(r_el, "Type", "1")  # 1 = Work
        cap = res.capacity_hours_per_day or 8.0
        _sub(r_el, "MaxUnits", str(round(cap / 8.0, 4)))
        res_uid_map[res.id] = i

    # ── Assignments ───────────────────────────────────────────────────────────
    assign_uid = 1
    for inst in instances:
        for stage in inst.stage_instances:
            for task in stage.task_instances:
                if task.assigned_resource_id and task.assigned_resource_id in res_uid_map:
                    a_el = ET.SubElement(assignments_el, "Assignment")
                    _sub(a_el, "UID", str(assign_uid))
                    _sub(a_el, "TaskUID", str(task_uid_map[task.id]))
                    _sub(a_el, "ResourceUID", str(res_uid_map[task.assigned_resource_id]))
                    _sub(a_el, "Units", "1")
                    assign_uid += 1

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def _sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def _ms_date(day_offset: int, anchor: date) -> str:
    """Return ISO 8601 datetime string for MS Project."""
    d = anchor + timedelta(days=day_offset)
    return d.strftime("%Y-%m-%dT08:00:00")
