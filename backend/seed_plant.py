"""
seed_plant.py — seeds the full GE plant DeltaV hierarchy from EquipHier.xml.

Structure mapped:
  Area (XML)        → Area model
  ProcessCell       → flattened (folded into Area description)
  Unit (XML)        → Unit model
  EquipmentModule   → Object (type='EM')
  ControlModule     → Object (type='CM', parent_object_id → owning EM if any)
  UnitPhase         → skipped

Removes all existing projects before seeding.

Run from the backend directory:
  python seed_plant.py [/path/to/EquipHier.xml]
"""

import sys
import uuid
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, date

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal
from app.models.project import Project, Area, Unit
from app.models.object import Object
from app.models.workflow import (
    WorkflowTemplate,
    WorkflowTemplateVersion,
    WorkflowInstance,
    StageInstance,
)
from app.models.readiness import ReadinessEvaluation

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

XML_PATH = r"C:\Users\admin\AppData\Local\Temp\EquipHier.xml"

PROJECT_NAME = "GE Plant DeltaV Upgrade"
PROJECT_DESC = (
    "Full commissioning and qualification programme for the GE biomanufacturing plant. "
    "Covers cell culture, buffer prep, harvest, purification, formulation, CIP, media prep, "
    "utilities, and supporting systems."
)

# Only these four areas are in scope; everything else is skipped.
KEEP_AREAS = {"GE_FORMULATION", "GE_HARVEST", "GE_PURIFICATION1", "GE_PURIFICATION2"}

# Skip these areas — all areas not in KEEP_AREAS are excluded.
# AREA_A is empty; DELTAV_HARDWARE is controller chassis (no process units).
SKIP_AREAS = {"AREA_A", "DELTAV_HARDWARE"}

# One owner per area — gives realistic cross-area assignment spread
AREA_OWNERS: dict[str, str] = {
    "GE_BUFFER_PREP":    "Sarah Mitchell",
    "GE_CELLCULTURE":    "James Wong",
    "GE_CIP":            "David Torres",
    "GE_CMS":            "Emma Williams",
    "GE_CMS_HH":         "Emma Williams",
    "GE_EMS":            "Robert Chen",
    "GE_FORMULATION":    "Lisa Park",
    "GE_HARV_3350":      "Michael O'Brien",
    "GE_HARVEST":        "Michael O'Brien",
    "GE_MEDIA_PREP":     "Sarah Mitchell",
    "GE_PURIFICATION1":  "Anna Kowalski",
    "GE_PURIFICATION2":  "Anna Kowalski",
    "GE_SHARED_TP":      "David Torres",
    "GE_UTILITIES":      "James Wong",
}

# Fallback owners for any unmapped area
FALLBACK_OWNERS = ["Sarah Mitchell", "James Wong", "David Torres", "Emma Williams", "Lisa Park"]

# Human-readable zone names derived from area name
ZONE_MAP: dict[str, str] = {
    "GE_BUFFER_PREP":    "Buffer Prep",
    "GE_CELLCULTURE":    "Cell Culture",
    "GE_CIP":            "CIP",
    "GE_CMS":            "CMS",
    "GE_CMS_HH":         "CMS HH",
    "GE_EMS":            "EMS",
    "GE_FORMULATION":    "Formulation",
    "GE_HARV_3350":      "Harvest 3350",
    "GE_HARVEST":        "Harvest",
    "GE_MEDIA_PREP":     "Media Prep",
    "GE_PURIFICATION1":  "Purification 1",
    "GE_PURIFICATION2":  "Purification 2",
    "GE_SHARED_TP":      "Shared TP",
    "GE_UTILITIES":      "Utilities",
}

STAGES = ["engineering", "fat_prep", "fat_execution", "sat_prep", "sat_execution"]

STAGE_META = {
    "engineering":   {"name": "Engineering",   "order": 1},
    "fat_prep":      {"name": "FAT Prep",       "order": 2},
    "fat_execution": {"name": "FAT Execution",  "order": 3},
    "sat_prep":      {"name": "SAT Prep",       "order": 4},
    "sat_execution": {"name": "SAT Execution",  "order": 5},
}

# Readiness profiles — weighted toward mid-progress for a realistic in-flight project
READINESS_PROFILES = [
    # (overall, fat_ready, sat_ready, blocker_count, weight)
    (0.97, True,  True,  0, 5),
    (0.93, True,  False, 0, 8),
    (0.85, True,  False, 1, 10),
    (0.75, False, False, 1, 15),
    (0.65, False, False, 2, 15),
    (0.50, False, False, 2, 12),
    (0.38, False, False, 3, 10),
    (0.22, False, False, 3, 8),
    (0.10, False, False, 4, 7),
]

_profiles_flat = [p for p in READINESS_PROFILES for _ in range(p[4])]  # expand weights

BLOCKER_TEMPLATES = [
    {"type": "task",       "entity_name": "Design review",       "reason": "Task 'Design review' not complete in current stage",      "severity": "blocking"},
    {"type": "document",   "entity_name": "FDS document",         "reason": "Functional Design Specification not yet approved",        "severity": "blocking"},
    {"type": "dependency", "entity_name": "Upstream EM",          "reason": "Upstream equipment module has not reached FAT Execution", "severity": "blocking"},
    {"type": "stage_gate", "entity_name": "FAT gate",             "reason": "FAT gate: all IO points must be verified first",          "severity": "warning"},
    {"type": "task",       "entity_name": "Calibration sign-off", "reason": "Calibration sign-off pending instrument engineer",        "severity": "blocking"},
    {"type": "document",   "entity_name": "IQ protocol",          "reason": "Installation Qualification protocol not approved",        "severity": "blocking"},
    {"type": "dependency", "entity_name": "CIP unit",             "reason": "CIP unit qualification not complete",                     "severity": "warning"},
]

TEMPLATE_DEFINITION = {
    "stages": [
        {
            "key": sk, "name": sm["name"], "order": sm["order"],
            "is_mandatory": True,
            "entry_criteria": [],
            "exit_criteria": [{"type": "all_tasks_complete"}],
            "tasks": [
                {"key": f"{sk}_task1", "name": "Primary task",      "order": 1, "is_mandatory": True},
                {"key": f"{sk}_task2", "name": "Engineering review", "order": 2, "is_mandatory": True},
                {"key": f"{sk}_task3", "name": "Sign-off",           "order": 3, "is_mandatory": True},
            ],
        }
        for sk, sm in STAGE_META.items()
    ]
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_blockers(count: int) -> list[dict]:
    return [
        {**BLOCKER_TEMPLATES[i % len(BLOCKER_TEMPLATES)], "entity_id": str(uuid.uuid4())}
        for i in range(count)
    ]


def pick_stage(rng: random.Random, readiness: float) -> str:
    """Pick a plausible active stage given overall readiness."""
    if readiness >= 0.85:
        return rng.choice(["sat_prep", "sat_execution"])
    if readiness >= 0.60:
        return rng.choice(["fat_execution", "sat_prep"])
    if readiness >= 0.35:
        return rng.choice(["fat_prep", "fat_execution"])
    return rng.choice(["engineering", "fat_prep"])


def make_workflow_and_readiness(
    db: Session,
    obj: Object,
    tmpl_ver_id: uuid.UUID,
    rng: random.Random,
    now: datetime,
) -> None:
    profile = rng.choice(_profiles_flat)
    overall, fat_ready, sat_ready, blocker_cnt, _ = profile
    active_stage = pick_stage(rng, overall)

    # SAT ready only plausible at sat_execution
    if sat_ready and active_stage != "sat_execution":
        sat_ready = False

    wi = WorkflowInstance(
        id=uuid.uuid4(),
        entity_type="object",
        entity_id=obj.id,
        template_version_id=tmpl_ver_id,
        status="active",
    )
    db.add(wi)
    db.flush()

    active_order = STAGE_META[active_stage]["order"]
    for sk, sm in STAGE_META.items():
        order = sm["order"]
        if order < active_order:
            status = "complete"
        elif order == active_order:
            status = "active"
        else:
            status = "pending"

        db.add(StageInstance(
            id=uuid.uuid4(),
            workflow_instance_id=wi.id,
            stage_key=sk,
            stage_name=sm["name"],
            stage_order=order,
            status=status,
            started_at=now if status in ("active", "complete") else None,
            completed_at=now if status == "complete" else None,
        ))

    blockers = make_blockers(blocker_cnt)
    tech  = min(overall + 0.05, 1.0)
    doc   = max(overall - 0.10, 0.0)
    db.add(ReadinessEvaluation(
        id=uuid.uuid4(),
        entity_type="object",
        entity_id=obj.id,
        technical_readiness=round(tech, 2),
        document_readiness=round(doc, 2),
        stage_readiness=round(overall, 2),
        overall_readiness=round(overall, 2),
        ready_for_fat=fat_ready,
        ready_for_sat=sat_ready,
        blockers=blockers,
        next_action=blockers[0]["reason"] if blockers else "Proceed to next stage",
        evaluated_at=now,
    ))


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------

def parse_xml(path: str):
    """
    Returns: list of area_dicts:
      {
        "name": str,
        "process_cell": str | None,    # first PC name (informational)
        "units": [
          {
            "name": str,
            "ems": [
              {"name": str, "cms": [str, ...]}
            ],
            "direct_cms": [str, ...]
          }
        ]
      }
    """
    with open(path, encoding="utf-16") as f:
        content = f.read()
    root = ET.fromstring(content)

    areas = []
    for area_node in root:
        area_name = (area_node.text or "").strip()
        if area_name in SKIP_AREAS or area_name not in KEEP_AREAS:
            continue

        process_cells = [n for n in area_node if n.get("level") == "ProcessCell"]

        # Flatten all units from all process cells
        units = []
        pc_names = []
        for pc in process_cells:
            pc_names.append((pc.text or "").strip())
            for unit_node in pc:
                if unit_node.get("level") != "Unit":
                    continue
                unit_name = (unit_node.text or "").strip()
                ems = []
                direct_cms = []
                for child in unit_node:
                    lvl = child.get("level")
                    if lvl == "EquipmentModule":
                        em_name = (child.text or "").strip()
                        cms = [
                            (c.text or "").strip()
                            for c in child
                            if c.get("level") == "ControlModule"
                        ]
                        ems.append({"name": em_name, "cms": cms})
                    elif lvl == "ControlModule":
                        direct_cms.append((child.text or "").strip())
                units.append({"name": unit_name, "ems": ems, "direct_cms": direct_cms})

        if not units:
            continue  # skip areas with no units (hardware-only areas already filtered)

        areas.append({
            "name": area_name,
            "process_cell": ", ".join(pc_names) if pc_names else None,
            "units": units,
        })

    return areas


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed(db: Session, xml_path: str) -> None:
    rng = random.Random(1234)
    now = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # 1. Wipe all existing data via raw SQL (avoids ORM cascade gaps)
    # ------------------------------------------------------------------
    print("Clearing existing data…")
    tables = [
        "task_instances",
        "stage_instances",
        "workflow_instances",
        "readiness_evaluations",
        "dependency_rules",
        "documents",
        "objects",
        "units",
        "areas",
        "projects",
        "workflow_template_versions",
        "workflow_templates",
    ]
    for t in tables:
        db.execute(text(f"DELETE FROM {t}"))
    db.commit()
    print("  Done.")

    # ------------------------------------------------------------------
    # 2. Workflow template
    # ------------------------------------------------------------------
    tmpl = WorkflowTemplate(
        id=uuid.uuid4(),
        name="DeltaV_Standard_v1",
        applies_to_type="object",
        description="Standard 5-stage DeltaV commissioning workflow",
    )
    db.add(tmpl)
    db.flush()

    tmpl_ver = WorkflowTemplateVersion(
        id=uuid.uuid4(),
        template_id=tmpl.id,
        version_number=1,
        definition=TEMPLATE_DEFINITION,
        is_active=True,
        created_at=now,
    )
    db.add(tmpl_ver)
    db.flush()
    print(f"Created workflow template: {tmpl.name}")

    # ------------------------------------------------------------------
    # 3. Project
    # ------------------------------------------------------------------
    project = Project(
        id=uuid.uuid4(),
        name=PROJECT_NAME,
        description=PROJECT_DESC,
    )
    db.add(project)
    db.flush()
    print(f"Created project: {project.name}  [{project.id}]")

    # ------------------------------------------------------------------
    # 4. Parse XML and create Areas → Units → Objects
    # ------------------------------------------------------------------
    print(f"Parsing {xml_path} …")
    area_data = parse_xml(xml_path)
    print(f"  Found {len(area_data)} areas with units")

    total_units = total_ems = total_cms = 0

    for ad in area_data:
        area_name = ad["name"]
        zone = ZONE_MAP.get(area_name, area_name.replace("_", " ").title())
        owner = AREA_OWNERS.get(area_name, rng.choice(FALLBACK_OWNERS))
        pc_desc = f"Process Cell: {ad['process_cell']}" if ad["process_cell"] else None

        area = Area(
            id=uuid.uuid4(),
            project_id=project.id,
            name=area_name,
            description=pc_desc,
        )
        db.add(area)
        db.flush()

        for ud in ad["units"]:
            unit = Unit(
                id=uuid.uuid4(),
                area_id=area.id,
                name=ud["name"],
                description=None,
            )
            db.add(unit)
            db.flush()
            total_units += 1

            # EMs and their child CMs
            for em_data in ud["ems"]:
                em_obj = Object(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    area_id=area.id,
                    unit_id=unit.id,
                    parent_object_id=None,
                    name=em_data["name"],
                    object_type="EM",
                    status="active",
                    zone=zone,
                    owner=owner,
                    planned_start=date(2025, rng.randint(1, 6), rng.randint(1, 28)),
                    planned_end=date(2026, rng.randint(1, 6), rng.randint(1, 28)),
                )
                db.add(em_obj)
                db.flush()
                total_ems += 1
                make_workflow_and_readiness(db, em_obj, tmpl_ver.id, rng, now)

                for cm_name in em_data["cms"]:
                    cm_obj = Object(
                        id=uuid.uuid4(),
                        project_id=project.id,
                        area_id=area.id,
                        unit_id=unit.id,
                        parent_object_id=em_obj.id,
                        name=cm_name,
                        object_type="CM",
                        status="active",
                        zone=zone,
                        owner=owner,
                        planned_start=date(2025, rng.randint(1, 6), rng.randint(1, 28)),
                        planned_end=date(2026, rng.randint(1, 6), rng.randint(1, 28)),
                    )
                    db.add(cm_obj)
                    db.flush()
                    total_cms += 1
                    make_workflow_and_readiness(db, cm_obj, tmpl_ver.id, rng, now)

            # Direct CMs (not under any EM)
            for cm_name in ud["direct_cms"]:
                cm_obj = Object(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    area_id=area.id,
                    unit_id=unit.id,
                    parent_object_id=None,
                    name=cm_name,
                    object_type="CM",
                    status="active",
                    zone=zone,
                    owner=owner,
                    planned_start=date(2025, rng.randint(1, 6), rng.randint(1, 28)),
                    planned_end=date(2026, rng.randint(1, 6), rng.randint(1, 28)),
                )
                db.add(cm_obj)
                db.flush()
                total_cms += 1
                make_workflow_and_readiness(db, cm_obj, tmpl_ver.id, rng, now)

        print(f"  OK {area_name}  ({len(ad['units'])} units)")

    db.commit()

    print()
    print("=" * 50)
    print(f"Seed complete.")
    print(f"  Areas  : {len(area_data)}")
    print(f"  Units  : {total_units}")
    print(f"  EMs    : {total_ems}")
    print(f"  CMs    : {total_cms}")
    print(f"  Total objects: {total_ems + total_cms}")
    print("=" * 50)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else XML_PATH
    db = SessionLocal()
    try:
        seed(db, path)
    finally:
        db.close()
