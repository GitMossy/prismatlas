"""
seed_workflow_templates.py — creates the four canonical DeltaV workflow templates:
  CM_Standard_v1   — Control Module
  EM_Standard_v1   — Equipment Module
  Phase_Standard_v1 — Phase
  Unit_Standard_v1  — Unit

Stages (in order):
  1. Engineering
  2. Internal Review / Test
  3. Code Complete
  4. FAT
  5. SAT

Cross-entity entry_criteria (type="entity_type_stage_complete") encode the
dependency hierarchy: CM → EM → Phase → Unit.  These are stored in the
template definition and are evaluated by the ReadinessEngine at runtime.

Run from the backend directory:
  python seed_workflow_templates.py
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.workflow import WorkflowTemplate, WorkflowTemplateVersion

# ---------------------------------------------------------------------------
# Shared stage skeleton builder
# ---------------------------------------------------------------------------

def _doc(document_type: str, required_status: str, label: str) -> dict:
    return {"type": "document_status", "document_type": document_type,
            "required_status": required_status, "label": label}

def _stage(stage_key: str, label: str) -> dict:
    return {"type": "stage_complete", "stage_key": stage_key, "label": label}

def _entity(entity_type: str, stage_key: str, label: str) -> dict:
    return {"type": "entity_type_stage_complete", "entity_type": entity_type,
            "stage_key": stage_key, "label": label}

def _tasks(*name_pairs) -> list[dict]:
    """Build task list from (key, name) pairs."""
    return [
        {"key": key, "name": name, "order": i + 1, "is_mandatory": True}
        for i, (key, name) in enumerate(name_pairs)
    ]

# ---------------------------------------------------------------------------
# Document entry/exit criteria (shared across all entity types)
# ---------------------------------------------------------------------------

ENTRY_ENGINEERING = [
    _doc("FRS", "draft", "FRS/SDS Drafted"),
]

ENTRY_INTERNAL_REVIEW = [
    _doc("FRS", "draft", "FRS/SDS Drafted"),
]

ENTRY_CODE_COMPLETE = [
    _stage("internal_review", "Internal Review Complete"),
]

EXIT_CODE_COMPLETE = [
    {"type": "all_tasks_complete"},
    _doc("FRS", "approved", "FRS/SDS Approved"),
]

ENTRY_FAT = [
    _stage("code_complete", "Code Complete"),
    _doc("FRS", "approved", "FRS/SDS Approved"),
    _doc("FAT_Protocol", "approved", "FAT Protocol Approved"),
]

EXIT_FAT = [
    {"type": "all_tasks_complete"},
    _doc("FAT_Post_Report", "approved", "FAT Post Report Approved"),
]

ENTRY_SAT = [
    _stage("fat", "FAT Complete"),
    _doc("FRS", "approved", "FRS/SDS Approved"),
    _doc("SAT_Protocol", "approved", "SAT Protocol Approved"),
    _doc("FAT_Post_Report", "approved", "FAT Post Report Approved"),
]

EXIT_DEFAULT = [{"type": "all_tasks_complete"}]

# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

def _build_definition(
    engineering_entry_extra: list = None,
    internal_review_entry_extra: list = None,
    code_complete_entry_extra: list = None,
    fat_entry_extra: list = None,
    sat_entry_extra: list = None,
    entity_label: str = "",
) -> dict:
    """Compose a 5-stage definition with optional cross-entity entry criteria."""

    def _extend(base: list, extra: list | None) -> list:
        return base + (extra or [])

    return {
        "stages": [
            {
                "key": "engineering",
                "name": "Engineering",
                "order": 1,
                "is_mandatory": True,
                "entry_criteria": _extend(ENTRY_ENGINEERING, engineering_entry_extra),
                "exit_criteria": EXIT_DEFAULT,
                "tasks": _tasks(
                    ("config_spec_draft",  "Configuration Specification Draft"),
                    ("config_review",      "Configuration Review"),
                    ("config_signoff",     "Configuration Sign-off"),
                ),
            },
            {
                "key": "internal_review",
                "name": "Internal Review / Test",
                "order": 2,
                "is_mandatory": True,
                "entry_criteria": _extend(
                    [_stage("engineering", f"{entity_label} Configuration Complete".strip())]
                    + ENTRY_INTERNAL_REVIEW,
                    internal_review_entry_extra,
                ),
                "exit_criteria": EXIT_DEFAULT,
                "tasks": _tasks(
                    ("internal_test_exec", "Internal Test Execution"),
                    ("peer_review",        "Peer Review"),
                    ("review_signoff",     "Review Sign-off"),
                ),
            },
            {
                "key": "code_complete",
                "name": "Code Complete",
                "order": 3,
                "is_mandatory": True,
                "entry_criteria": _extend(ENTRY_CODE_COMPLETE, code_complete_entry_extra),
                "exit_criteria": EXIT_CODE_COMPLETE,
                "tasks": _tasks(
                    ("code_finalization", "Code Finalization"),
                    ("code_review",       "Code Review"),
                    ("frs_approval",      "FRS/SDS Approval"),
                ),
            },
            {
                "key": "fat",
                "name": "FAT",
                "order": 4,
                "is_mandatory": True,
                "entry_criteria": _extend(ENTRY_FAT, fat_entry_extra),
                "exit_criteria": EXIT_FAT,
                "tasks": _tasks(
                    ("fat_protocol_review",      "FAT Protocol Review"),
                    ("fat_execution",            "FAT Execution"),
                    ("fat_report_draft",         "FAT Report Draft"),
                    ("fat_post_report_approval", "FAT Post Report Approval"),
                ),
            },
            {
                "key": "sat",
                "name": "SAT",
                "order": 5,
                "is_mandatory": True,
                "entry_criteria": _extend(ENTRY_SAT, sat_entry_extra),
                "exit_criteria": EXIT_DEFAULT,
                "tasks": _tasks(
                    ("sat_protocol_review", "SAT Protocol Review"),
                    ("sat_execution",       "SAT Execution"),
                    ("sat_report_draft",    "SAT Report Draft"),
                    ("sat_final_signoff",   "Final Sign-off"),
                ),
            },
        ]
    }


# CM — no cross-entity dependencies
CM_DEFINITION = _build_definition(entity_label="CM")

# EM — depends on CM at every stage except Engineering
EM_DEFINITION = _build_definition(
    entity_label="EM",
    internal_review_entry_extra=[
        _entity("CM", "internal_review", "CM Internal Review Complete"),
    ],
    code_complete_entry_extra=[
        _entity("CM", "code_complete", "CM Code Complete"),
    ],
    fat_entry_extra=[
        _entity("CM", "fat", "CM FAT Complete"),
    ],
    sat_entry_extra=[
        _entity("CM", "sat", "CM SAT Complete"),
    ],
)

# Phase — depends on EM + CM; Engineering also requires EM + CM config complete
PHASE_DEFINITION = _build_definition(
    entity_label="Phase",
    engineering_entry_extra=[
        _entity("EM", "engineering", "EM Configuration Complete"),
        _entity("CM", "engineering", "CM Configuration Complete"),
    ],
    internal_review_entry_extra=[
        _entity("EM", "internal_review", "EM Internal Review Complete"),
        _entity("CM", "internal_review", "CM Internal Review Complete"),
    ],
    code_complete_entry_extra=[
        _entity("EM", "code_complete", "EM Code Complete"),
        _entity("CM", "code_complete", "CM Code Complete"),
    ],
    fat_entry_extra=[
        _entity("EM", "fat", "EM FAT Complete"),
        _entity("CM", "fat", "CM FAT Complete"),
    ],
    sat_entry_extra=[
        _entity("EM", "sat", "EM SAT Complete"),
        _entity("CM", "sat", "CM SAT Complete"),
    ],
)

# Unit — depends on Phase + EM + CM at every stage (no extra engineering deps per table)
UNIT_DEFINITION = _build_definition(
    entity_label="Unit",
    internal_review_entry_extra=[
        _entity("Phase", "internal_review", "Phase Internal Review Complete"),
        _entity("EM",    "internal_review", "EM Internal Review Complete"),
        _entity("CM",    "internal_review", "CM Internal Review Complete"),
    ],
    code_complete_entry_extra=[
        _entity("Phase", "code_complete", "Phase Code Complete"),
        _entity("EM",    "code_complete", "EM Code Complete"),
        _entity("CM",    "code_complete", "CM Code Complete"),
    ],
    fat_entry_extra=[
        _entity("Phase", "fat", "Phase FAT Complete"),
        _entity("EM",    "fat", "EM FAT Complete"),
        _entity("CM",    "fat", "CM FAT Complete"),
    ],
    sat_entry_extra=[
        _entity("Phase", "sat", "Phase SAT Complete"),
        _entity("EM",    "sat", "EM SAT Complete"),
        _entity("CM",    "sat", "CM SAT Complete"),
    ],
)

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        "name": "CM_Standard_v1",
        "applies_to_type": "CM",
        "description": "Standard 5-stage commissioning workflow for Control Modules. "
                       "No cross-entity dependencies — CM is the base layer.",
        "definition": CM_DEFINITION,
    },
    {
        "name": "EM_Standard_v1",
        "applies_to_type": "EM",
        "description": "Standard 5-stage commissioning workflow for Equipment Modules. "
                       "Requires CM completion at each stage from Internal Review onward.",
        "definition": EM_DEFINITION,
    },
    {
        "name": "Phase_Standard_v1",
        "applies_to_type": "Phase",
        "description": "Standard 5-stage commissioning workflow for Phases. "
                       "Requires EM and CM completion at each stage; "
                       "Engineering additionally requires EM and CM to be configuration-complete.",
        "definition": PHASE_DEFINITION,
    },
    {
        "name": "Unit_Standard_v1",
        "applies_to_type": "Unit",
        "description": "Standard 5-stage commissioning workflow for Units. "
                       "Requires Phase, EM, and CM completion at each stage from "
                       "Internal Review onward.",
        "definition": UNIT_DEFINITION,
    },
]

# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed(db: Session) -> None:
    now = datetime.now(timezone.utc)

    for tmpl_spec in TEMPLATES:
        existing = (
            db.query(WorkflowTemplate)
            .filter(WorkflowTemplate.name == tmpl_spec["name"])
            .first()
        )
        if existing:
            print(f"[skip] {tmpl_spec['name']} already exists")
            continue

        tmpl = WorkflowTemplate(
            id=uuid.uuid4(),
            name=tmpl_spec["name"],
            applies_to_type=tmpl_spec["applies_to_type"],
            description=tmpl_spec["description"],
        )
        db.add(tmpl)
        db.flush()

        ver = WorkflowTemplateVersion(
            id=uuid.uuid4(),
            template_id=tmpl.id,
            version_number=1,
            definition=tmpl_spec["definition"],
            is_active=True,
            created_at=now,
        )
        db.add(ver)
        db.flush()

        print(f"[created] {tmpl_spec['name']}  template={tmpl.id}  version={ver.id}")

    db.commit()
    print("Done.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
