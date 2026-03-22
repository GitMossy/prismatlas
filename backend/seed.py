"""
Seed script — populates a project with objects spread across all cube dimensions:
  zones        : Room A, Room B, Room C, Room D
  object_types : EM, IO, CM, Phase
  stages       : engineering, fat_prep, fat_execution, sat_prep, sat_execution
  owners       : Alice Chen, Bob Singh, Carol Diaz

Run from the backend directory:
  python seed.py
"""

import uuid
from datetime import datetime, timezone, date
import random

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.project import Project
from app.models.object import Object
from app.models.workflow import (
    WorkflowTemplate,
    WorkflowTemplateVersion,
    WorkflowInstance,
    StageInstance,
)
from app.models.readiness import ReadinessEvaluation

# ---------------------------------------------------------------------------
# Dimension pools
# ---------------------------------------------------------------------------

ZONES        = ["Room A", "Room B", "Room C", "Room D"]
OBJECT_TYPES = ["EM", "IO", "CM", "Phase"]
OWNERS       = ["Alice Chen", "Bob Singh", "Carol Diaz"]
STAGES       = ["engineering", "fat_prep", "fat_execution", "sat_prep", "sat_execution"]

STAGE_META = {
    "engineering":    {"name": "Engineering",    "order": 1},
    "fat_prep":       {"name": "FAT Prep",        "order": 2},
    "fat_execution":  {"name": "FAT Execution",   "order": 3},
    "sat_prep":       {"name": "SAT Prep",        "order": 4},
    "sat_execution":  {"name": "SAT Execution",   "order": 5},
}

# Readiness values that give a nice spread of colours
READINESS_PROFILES = [
    # (overall, fat_ready, sat_ready, blocker_count)
    (0.95, True,  True,  0),
    (0.90, True,  False, 0),
    (0.75, False, False, 1),
    (0.60, False, False, 2),
    (0.40, False, False, 3),
    (0.20, False, False, 4),
]

TEMPLATE_DEFINITION = {
    "stages": [
        {
            "key": sk,
            "name": sm["name"],
            "order": sm["order"],
            "is_mandatory": True,
            "entry_criteria": [],
            "exit_criteria": [{"type": "all_tasks_complete"}],
            "tasks": [
                {"key": f"{sk}_task1", "name": "Primary task", "order": 1, "is_mandatory": True},
                {"key": f"{sk}_task2", "name": "Review",       "order": 2, "is_mandatory": True},
            ],
        }
        for sk, sm in STAGE_META.items()
    ]
}


def make_blockers(count: int, stage: str) -> list[dict]:
    templates = [
        {"type": "task",        "entity_name": "Design review",      "reason": f"Task 'Design review' not complete in {stage}",         "severity": "blocking"},
        {"type": "document",    "entity_name": "FRS document",        "reason": "FRS document not yet approved",                         "severity": "blocking"},
        {"type": "dependency",  "entity_name": "Upstream EM",         "reason": "Upstream EM has not reached FAT Execution",             "severity": "blocking"},
        {"type": "stage_gate",  "entity_name": "FAT gate",            "reason": "FAT gate requires all IO points verified",              "severity": "warning"},
        {"type": "task",        "entity_name": "Calibration sign-off","reason": "Calibration sign-off pending instrument engineer",      "severity": "blocking"},
    ]
    return [
        {**t, "entity_id": str(uuid.uuid4())}
        for t in templates[:count]
    ]


def seed(db: Session) -> None:
    # ------------------------------------------------------------------
    # 1. Project
    # ------------------------------------------------------------------
    project = db.query(Project).filter(Project.name == "DeltaV Plant Upgrade").first()
    if project is None:
        project = Project(
            id=uuid.uuid4(),
            name="DeltaV Plant Upgrade",
            description="Full plant commissioning and qualification project.",
        )
        db.add(project)
        db.flush()
        print(f"Created project: {project.name}  [{project.id}]")
    else:
        print(f"Using existing project: {project.name}  [{project.id}]")

    # ------------------------------------------------------------------
    # 2. Workflow template (one shared template)
    # ------------------------------------------------------------------
    tmpl = db.query(WorkflowTemplate).filter(WorkflowTemplate.name == "Standard_v1").first()
    if tmpl is None:
        tmpl = WorkflowTemplate(
            id=uuid.uuid4(),
            name="Standard_v1",
            applies_to_type="object",
            description="Standard 5-stage commissioning workflow",
        )
        db.add(tmpl)
        db.flush()

        tmpl_ver = WorkflowTemplateVersion(
            id=uuid.uuid4(),
            template_id=tmpl.id,
            version_number=1,
            definition=TEMPLATE_DEFINITION,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(tmpl_ver)
        db.flush()
        print("Created workflow template Standard_v1 v1")
    else:
        tmpl_ver = (
            db.query(WorkflowTemplateVersion)
            .filter(WorkflowTemplateVersion.template_id == tmpl.id)
            .order_by(WorkflowTemplateVersion.version_number.desc())
            .first()
        )
        print(f"Using existing template version: {tmpl_ver.id}")

    # ------------------------------------------------------------------
    # 3. Objects — one per (zone × object_type × stage) sample
    #    We don't create all 80 combinations; instead we create ~50 objects
    #    spread to ensure every dimension value appears.
    # ------------------------------------------------------------------
    existing_names = {o.name for o in db.query(Object.name).filter(Object.project_id == project.id).all()}

    rng = random.Random(42)  # deterministic

    objects_created = 0

    # Ensure every (zone, object_type, stage) trio has at least one object
    combos = [
        (zone, obj_type, stage)
        for zone      in ZONES
        for obj_type  in OBJECT_TYPES
        for stage     in STAGES
    ]
    # Shuffle so readiness profiles are varied
    rng.shuffle(combos)

    new_objects: list[tuple[Object, str]] = []  # (object, active_stage)

    for i, (zone, obj_type, stage) in enumerate(combos):
        name = f"{obj_type}-{zone.replace(' ', '')}-{stage[:3].upper()}-{i+1:03d}"
        if name in existing_names:
            continue

        owner       = rng.choice(OWNERS)
        profile_idx = rng.randint(0, len(READINESS_PROFILES) - 1)
        readiness, fat_ready, sat_ready, blocker_cnt = READINESS_PROFILES[profile_idx]

        # Snap SAT-ready only if stage is sat_execution
        if sat_ready and stage != "sat_execution":
            sat_ready = False

        obj = Object(
            id=uuid.uuid4(),
            project_id=project.id,
            name=name,
            object_type=obj_type,
            status="active",
            zone=zone,
            owner=owner,
            planned_start=date(2025, rng.randint(1, 6), rng.randint(1, 28)),
            planned_end=date(2025, rng.randint(7, 12), rng.randint(1, 28)),
        )
        db.add(obj)
        new_objects.append((obj, stage, readiness, fat_ready, sat_ready, blocker_cnt))
        objects_created += 1

    db.flush()
    print(f"Created {objects_created} objects")

    # ------------------------------------------------------------------
    # 4. WorkflowInstances + active StageInstances + ReadinessEvaluations
    # ------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    evals_created = 0

    for obj, active_stage, readiness, fat_ready, sat_ready, blocker_cnt in new_objects:
        # WorkflowInstance
        wi = WorkflowInstance(
            id=uuid.uuid4(),
            entity_type="object",
            entity_id=obj.id,
            template_version_id=tmpl_ver.id,
            status="active",
        )
        db.add(wi)
        db.flush()

        # Create all stage instances; mark the active stage as "active", previous as "complete"
        active_order = STAGE_META[active_stage]["order"]
        for sk, sm in STAGE_META.items():
            order = sm["order"]
            if order < active_order:
                status = "complete"
            elif order == active_order:
                status = "active"
            else:
                status = "pending"

            si = StageInstance(
                id=uuid.uuid4(),
                workflow_instance_id=wi.id,
                stage_key=sk,
                stage_name=sm["name"],
                stage_order=order,
                status=status,
                started_at=now if status in ("active", "complete") else None,
                completed_at=now if status == "complete" else None,
            )
            db.add(si)

        # ReadinessEvaluation
        blockers = make_blockers(blocker_cnt, active_stage)
        next_action = blockers[0]["reason"] if blockers else "Proceed to next stage"

        # derive sub-dimensions from overall
        tech = min(readiness + 0.05, 1.0)
        doc  = max(readiness - 0.10, 0.0)
        stage_r = readiness

        ev = ReadinessEvaluation(
            id=uuid.uuid4(),
            entity_type="object",
            entity_id=obj.id,
            technical_readiness=round(tech, 2),
            document_readiness=round(doc, 2),
            stage_readiness=round(stage_r, 2),
            overall_readiness=round(readiness, 2),
            ready_for_fat=fat_ready,
            ready_for_sat=sat_ready,
            blockers=blockers,
            next_action=next_action,
            evaluated_at=now,
        )
        db.add(ev)
        evals_created += 1

    db.commit()
    print(f"Created {evals_created} readiness evaluations")
    print("Seed complete.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
