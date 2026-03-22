"""
Seed script: creates a full example project for UI testing.
Run from repo root: python seed_example.py
"""
import requests, json, sys

BASE = "http://localhost:8000"

def post(path, body, params=None):
    r = requests.post(f"{BASE}{path}", json=body, params=params)
    if r.status_code not in (200, 201):
        print(f"ERROR {r.status_code} POST {path}: {r.text[:300]}")
        sys.exit(1)
    return r.json()

def put(path, body):
    r = requests.put(f"{BASE}{path}", json=body)
    if r.status_code not in (200, 201):
        print(f"ERROR {r.status_code} PUT {path}: {r.text[:300]}")
        sys.exit(1)
    return r.json()

def get(path):
    r = requests.get(f"{BASE}{path}")
    return r.json()

print("=== Creating project ===")
project = post("/projects", {
    "name": "Reactor Control Upgrade – Phase 2",
    "description": "Full DeltaV migration for the Reactor Control system across three production areas."
})
pid = project["id"]
print(f"  Project: {pid}")

# ── Areas ──────────────────────────────────────────────────
print("\n=== Creating areas ===")
area_a = post("/areas", {"project_id": pid, "name": "Area A – Reactor Core",    "description": "Primary reactor control loops"})
area_b = post("/areas", {"project_id": pid, "name": "Area B – Utilities",       "description": "Steam, cooling water, compressed air"})
area_c = post("/areas", {"project_id": pid, "name": "Area C – Safety Systems",  "description": "ESD and fire & gas"})
for a in [area_a, area_b, area_c]:
    print(f"  {a['name']}: {a['id']}")

# ── Units ──────────────────────────────────────────────────
print("\n=== Creating units ===")
unit_rx1  = post("/units", {"area_id": area_a["id"], "name": "RX-1 Primary Loop",    "description": "Primary coolant loop"})
unit_rx2  = post("/units", {"area_id": area_a["id"], "name": "RX-2 Secondary Loop",  "description": "Secondary heat exchange"})
unit_util = post("/units", {"area_id": area_b["id"], "name": "Utility Distribution", "description": "Steam & CW distribution"})
unit_esd  = post("/units", {"area_id": area_c["id"], "name": "ESD Logic",            "description": "Emergency shutdown logic"})

# ── Workflow template ──────────────────────────────────────
print("\n=== Creating workflow template ===")
import uuid as _uuid
tmpl = post("/workflow-templates", {
    "name": f"EM_Standard_{_uuid.uuid4().hex[:6]}",
    "applies_to_type": "EM",
    "description": "Standard EM commissioning workflow"
})
tmpl_id = tmpl["id"]

version = post(f"/workflow-templates/{tmpl_id}/versions", {
    "definition": {
        "stages": [
            {
                "key": "engineering",
                "name": "Engineering",
                "order": 1,
                "is_mandatory": True,
                "entry_criteria": [],
                "exit_criteria": [{"type": "all_tasks_complete"}],
                "tasks": [
                    {"key": "design_review",   "name": "Design Review Complete",   "order": 1, "is_mandatory": True},
                    {"key": "config_complete",  "name": "Configuration Complete",   "order": 2, "is_mandatory": True},
                    {"key": "code_review",      "name": "Code Review Passed",       "order": 3, "is_mandatory": True},
                ]
            },
            {
                "key": "fat_prep",
                "name": "FAT Preparation",
                "order": 2,
                "is_mandatory": True,
                "entry_criteria": [{"type": "stage_complete", "stage_key": "engineering"}],
                "exit_criteria": [{"type": "all_tasks_complete"}],
                "tasks": [
                    {"key": "test_plan",       "name": "FAT Test Plan Approved",   "order": 1, "is_mandatory": True},
                    {"key": "io_checkout",     "name": "I/O Checkout Complete",    "order": 2, "is_mandatory": True},
                ]
            },
            {
                "key": "fat_execution",
                "name": "FAT Execution",
                "order": 3,
                "is_mandatory": True,
                "entry_criteria": [{"type": "stage_complete", "stage_key": "fat_prep"}],
                "exit_criteria": [{"type": "all_tasks_complete"}],
                "tasks": [
                    {"key": "fat_run",         "name": "FAT Witnessed & Passed",   "order": 1, "is_mandatory": True},
                    {"key": "punch_closed",    "name": "Punch List Closed",        "order": 2, "is_mandatory": True},
                ]
            },
            {
                "key": "sat_prep",
                "name": "SAT Preparation",
                "order": 4,
                "is_mandatory": True,
                "entry_criteria": [{"type": "stage_complete", "stage_key": "fat_execution"}],
                "exit_criteria": [{"type": "all_tasks_complete"}],
                "tasks": [
                    {"key": "site_ready",      "name": "Site Readiness Confirmed", "order": 1, "is_mandatory": True},
                    {"key": "loop_check",      "name": "Loop Check Complete",      "order": 2, "is_mandatory": True},
                ]
            },
            {
                "key": "sat_execution",
                "name": "SAT Execution",
                "order": 5,
                "is_mandatory": True,
                "entry_criteria": [{"type": "stage_complete", "stage_key": "sat_prep"}],
                "exit_criteria": [{"type": "all_tasks_complete"}],
                "tasks": [
                    {"key": "sat_run",         "name": "SAT Witnessed & Passed",   "order": 1, "is_mandatory": True},
                    {"key": "handover",        "name": "Handover Documentation",   "order": 2, "is_mandatory": True},
                ]
            },
        ]
    }
})
ver_id = version["id"]
print(f"  Template version: {ver_id}")

# ── Objects ────────────────────────────────────────────────
print("\n=== Creating objects ===")

objects_spec = [
    # name, type, area, unit, zone, owner, planned_start, planned_end, status
    ("RX-101 Temperature Controller",  "EM", area_a, unit_rx1,  "Room A1", "Alice Chen",    "2026-04-01", "2026-06-30", "active"),
    ("RX-102 Pressure Controller",     "EM", area_a, unit_rx1,  "Room A1", "Alice Chen",    "2026-04-01", "2026-06-30", "active"),
    ("RX-103 Flow Controller",         "EM", area_a, unit_rx1,  "Room A2", "Bob Martinez",  "2026-04-15", "2026-07-15", "active"),
    ("RX-201 Heat Exchanger Control",  "EM", area_a, unit_rx2,  "Room A2", "Bob Martinez",  "2026-05-01", "2026-07-31", "active"),
    ("RX-202 Level Controller",        "EM", area_a, unit_rx2,  "Room A2", "Alice Chen",    "2026-05-01", "2026-07-31", "active"),
    ("UT-101 Steam Flow",              "EM", area_b, unit_util, "Room B1", "Carol Singh",   "2026-04-01", "2026-06-15", "active"),
    ("UT-102 CW Return Temp",          "EM", area_b, unit_util, "Room B1", "Carol Singh",   "2026-04-01", "2026-06-15", "active"),
    ("UT-103 Air Pressure",            "EM", area_b, unit_util, "Room B2", "David Kim",     "2026-04-15", "2026-06-30", "active"),
    ("ESD-001 Reactor Trip",           "EM", area_c, unit_esd,  "Room C1", "Eve Okafor",    "2026-03-15", "2026-05-31", "active"),
    ("ESD-002 Coolant Isolation",      "EM", area_c, unit_esd,  "Room C1", "Eve Okafor",    "2026-03-15", "2026-05-31", "active"),
    ("IO-RX-001 AI Cards",             "IO", area_a, unit_rx1,  "Room A1", "Alice Chen",    "2026-03-01", "2026-04-30", "active"),
    ("IO-RX-002 AO Cards",             "IO", area_a, unit_rx1,  "Room A1", "Alice Chen",    "2026-03-01", "2026-04-30", "active"),
    ("IO-UT-001 DI/DO Cards",          "IO", area_b, unit_util, "Room B1", "Carol Singh",   "2026-03-01", "2026-04-15", "active"),
    ("CM-RX-001 S-Series Controller",  "CM", area_a, unit_rx1,  "Room A1", "Bob Martinez",  "2026-02-15", "2026-03-31", "active"),
    ("CM-ESD-001 SIS Controller",      "CM", area_c, unit_esd,  "Room C1", "Eve Okafor",    "2026-02-15", "2026-03-31", "active"),
    ("PH-STARTUP-001 Startup Phase",   "Phase", area_a, unit_rx1, "Room A1", "Alice Chen",  "2026-07-01", "2026-08-15", "active"),
]

obj_ids = {}
for name, otype, area, unit, zone, owner, ps, pe, status in objects_spec:
    obj = post("/objects", {
        "project_id": pid,
        "area_id": area["id"],
        "unit_id": unit["id"],
        "name": name,
        "object_type": otype,
        "status": status,
        "zone": zone,
        "owner": owner,
        "planned_start": ps,
        "planned_end": pe,
    })
    obj_ids[name] = obj["id"]
    print(f"  {name}: {obj['id']}")

# ── Documents ──────────────────────────────────────────────
print("\n=== Creating documents ===")

docs_spec = [
    ("RX-101 Functional Requirements Spec", "FRS",  "In_Review", "Specification for RX-101 TC"),
    ("RX-101 Software Design Document",     "SDD",  "Draft",     "Software design for RX-101 TC"),
    ("RX-101 FAT Protocol",                 "FAT",  "Draft",     "FAT test protocol for RX-101"),
    ("RX-102 Functional Requirements Spec", "FRS",  "Approved",  "Specification for RX-102 PC"),
    ("RX-102 FAT Protocol",                 "FAT",  "In_Review", "FAT test protocol for RX-102"),
    ("ESD-001 Safety Requirements Spec",    "FRS",  "Approved",  "SRS for ESD-001 Reactor Trip"),
    ("ESD-001 FAT Protocol",                "FAT",  "Approved",  "FAT protocol for ESD-001"),
    ("ESD-001 SAT Protocol",                "SAT",  "In_Review", "SAT protocol for ESD-001"),
    ("Project FAT Plan",                    "FAT",  "Approved",  "Master FAT execution plan"),
    ("Project SAT Plan",                    "SAT",  "Draft",     "Master SAT execution plan"),
    ("RX-103 Functional Requirements Spec", "FRS",  "Draft",     "Specification for RX-103 FC"),
    ("UT-101 FAT Protocol",                 "FAT",  "Draft",     "FAT test protocol for UT-101"),
]

doc_ids = {}
for name, dtype, status, desc in docs_spec:
    doc = post("/documents", {
        "project_id": pid,
        "name": name,
        "document_type": dtype,
        "status": status,
        "description": desc,
    })
    doc_ids[name] = doc["id"]
    print(f"  {name}: {doc['id']}")

# ── Relationships (object ↔ document) ─────────────────────
print("\n=== Creating relationships ===")

rels = [
    ("object", obj_ids["RX-101 Temperature Controller"], "document", doc_ids["RX-101 Functional Requirements Spec"], "requires", True),
    ("object", obj_ids["RX-101 Temperature Controller"], "document", doc_ids["RX-101 Software Design Document"],     "requires", True),
    ("object", obj_ids["RX-101 Temperature Controller"], "document", doc_ids["RX-101 FAT Protocol"],                "requires", True),
    ("object", obj_ids["RX-102 Pressure Controller"],    "document", doc_ids["RX-102 Functional Requirements Spec"],"requires", True),
    ("object", obj_ids["RX-102 Pressure Controller"],    "document", doc_ids["RX-102 FAT Protocol"],                "requires", True),
    ("object", obj_ids["ESD-001 Reactor Trip"],          "document", doc_ids["ESD-001 Safety Requirements Spec"],   "requires", True),
    ("object", obj_ids["ESD-001 Reactor Trip"],          "document", doc_ids["ESD-001 FAT Protocol"],               "requires", True),
    ("object", obj_ids["ESD-001 Reactor Trip"],          "document", doc_ids["ESD-001 SAT Protocol"],               "requires", True),
    ("object", obj_ids["RX-101 Temperature Controller"], "object",   obj_ids["IO-RX-001 AI Cards"],                 "depends_on", True),
    ("object", obj_ids["RX-102 Pressure Controller"],    "object",   obj_ids["IO-RX-001 AI Cards"],                 "depends_on", True),
    ("object", obj_ids["RX-101 Temperature Controller"], "object",   obj_ids["CM-RX-001 S-Series Controller"],      "depends_on", True),
    ("object", obj_ids["ESD-001 Reactor Trip"],          "object",   obj_ids["CM-ESD-001 SIS Controller"],          "depends_on", True),
    ("object", obj_ids["UT-101 Steam Flow"],             "document", doc_ids["UT-101 FAT Protocol"],                "requires", True),
    ("object", obj_ids["RX-103 Flow Controller"],        "document", doc_ids["RX-103 Functional Requirements Spec"],"requires", True),
]

for se_type, se_id, te_type, te_id, rtype, mandatory in rels:
    rel = post("/relationships", {
        "source_entity_type": se_type,
        "source_entity_id": str(se_id),
        "target_entity_type": te_type,
        "target_entity_id": str(te_id),
        "relationship_type": rtype,
        "is_mandatory": mandatory,
    })
    print(f"  Relationship: {rel['id']}")

# ── Workflow instances ─────────────────────────────────────
print("\n=== Creating workflow instances ===")

# Create instances for all EM/Phase objects
em_objects = [(n, i) for n, i in obj_ids.items()
              if any(n.startswith(p) for p in ("RX-", "UT-", "ESD-", "PH-"))]

wf_instances = {}
for name, oid in em_objects:
    wf = post(f"/entities/{oid}/workflow", {"template_version_id": ver_id}, params={"entity_type": "object"})
    wf_instances[name] = wf
    print(f"  Workflow for {name}: {wf['id']}")

# ── Advance stages to realistic positions ─────────────────
print("\n=== Advancing stages to realistic positions ===")

def complete_task(entity_id, task_id):
    put(f"/entities/{entity_id}/workflow/tasks/{task_id}/complete", {
        "completed_by": "seed_script",
        "notes": "Completed during seed"
    })

def advance_stage(entity_id, stage_id):
    r = requests.post(f"{BASE}/entities/{entity_id}/workflow/stages/{stage_id}/advance")
    return r.json()

def get_workflow(entity_id):
    return get(f"/entities/{entity_id}/workflow")

def complete_stage_tasks(entity_id, stage, task_keys):
    """Complete specified tasks in a stage."""
    for task in stage["task_instances"]:
        if task["task_key"] in task_keys:
            complete_task(entity_id, task["id"])

def get_stage(wf, stage_key):
    for s in wf["stage_instances"]:
        if s["stage_key"] == stage_key:
            return s
    return None

# ESD-001: furthest along — FAT execution complete, in SAT prep
print("  ESD-001 Reactor Trip -> SAT prep (active)...")
oid = obj_ids["ESD-001 Reactor Trip"]
wf = get_workflow(oid)
# Complete engineering
s = get_stage(wf, "engineering")
complete_stage_tasks(oid, s, ["design_review", "config_complete", "code_review"])
advance_stage(oid, s["id"])
wf = get_workflow(oid)
# Complete fat_prep
s = get_stage(wf, "fat_prep")
complete_stage_tasks(oid, s, ["test_plan", "io_checkout"])
advance_stage(oid, s["id"])
wf = get_workflow(oid)
# Complete fat_execution
s = get_stage(wf, "fat_execution")
complete_stage_tasks(oid, s, ["fat_run", "punch_closed"])
advance_stage(oid, s["id"])
print("    Done.")

# ESD-002: FAT prep active, 1 task done
print("  ESD-002 Coolant Isolation -> FAT prep (partially done)...")
oid = obj_ids["ESD-002 Coolant Isolation"]
wf = get_workflow(oid)
s = get_stage(wf, "engineering")
complete_stage_tasks(oid, s, ["design_review", "config_complete", "code_review"])
advance_stage(oid, s["id"])
wf = get_workflow(oid)
s = get_stage(wf, "fat_prep")
complete_stage_tasks(oid, s, ["test_plan"])
print("    Done.")

# RX-102: engineering complete, FAT prep active
print("  RX-102 Pressure Controller -> FAT prep (active)...")
oid = obj_ids["RX-102 Pressure Controller"]
wf = get_workflow(oid)
s = get_stage(wf, "engineering")
complete_stage_tasks(oid, s, ["design_review", "config_complete", "code_review"])
advance_stage(oid, s["id"])
print("    Done.")

# CM-RX-001: engineering fully done, FAT prep active
print("  CM-RX-001 -> FAT prep (active)...")
oid = obj_ids["CM-RX-001 S-Series Controller"]
wf = get_workflow(oid)
s = get_stage(wf, "engineering")
complete_stage_tasks(oid, s, ["design_review", "config_complete", "code_review"])
advance_stage(oid, s["id"])
print("    Done.")

# RX-101: engineering in progress (2/3 tasks done)
print("  RX-101 Temperature Controller -> engineering (2/3 tasks)...")
oid = obj_ids["RX-101 Temperature Controller"]
wf = get_workflow(oid)
s = get_stage(wf, "engineering")
complete_stage_tasks(oid, s, ["design_review", "config_complete"])
print("    Done.")

# IO-RX-001/002: engineering complete
for name in ["IO-RX-001 AI Cards", "IO-RX-002 AO Cards"]:
    print(f"  {name} -> engineering complete...")
    oid = obj_ids[name]
    wf = get_workflow(oid)
    s = get_stage(wf, "engineering")
    complete_stage_tasks(oid, s, ["design_review", "config_complete", "code_review"])
    advance_stage(oid, s["id"])
print("    Done.")

# CM-ESD-001: all engineering tasks done
print("  CM-ESD-001 -> FAT prep active...")
oid = obj_ids["CM-ESD-001 SIS Controller"]
wf = get_workflow(oid)
s = get_stage(wf, "engineering")
complete_stage_tasks(oid, s, ["design_review", "config_complete", "code_review"])
advance_stage(oid, s["id"])
print("    Done.")

# ── Trigger readiness evaluations ─────────────────────────
print("\n=== Evaluating readiness for all entities ===")

all_entity_ids = list(obj_ids.values()) + list(doc_ids.values())
for eid, etype in [(i, "object") for i in obj_ids.values()] + [(i, "document") for i in doc_ids.values()]:
    r = requests.post(f"{BASE}/entities/{eid}/readiness/evaluate", params={"entity_type": etype})
    if r.status_code == 200:
        data = r.json()
        print(f"  {eid[:8]}… readiness={data['overall_readiness']:.0%} blockers={len(data['blockers'])}")
    else:
        print(f"  {eid[:8]}… skipped ({r.status_code}): {r.text[:100]}")

print("\n=== Done! ===")
print(f"\nProject ID: {pid}")
print(f"Open: http://localhost:5174")
print(f"Select project: 'Reactor Control Upgrade – Phase 2'")
