"""Finish the seed: advance stages + evaluate readiness for the already-created project."""
import sys
import requests

BASE = "http://localhost:8000"

def put(path, body=None):
    r = requests.put(f"{BASE}{path}", json=body or {})
    return r

def post(path, params=None, body=None):
    r = requests.post(f"{BASE}{path}", json=body or {}, params=params)
    return r

def get(path):
    r = requests.get(f"{BASE}{path}")
    return r.json()

# IDs from the last successful seed run
obj_ids = {
    "RX-101 Temperature Controller":  "45b7ae61-4953-4b4f-b2b0-98c67104a555",
    "RX-102 Pressure Controller":     "cc836eb3-60db-453f-9f81-8fa07def6634",
    "RX-103 Flow Controller":         "58f997f2-021d-4ecf-9957-ceb1685daac4",
    "RX-201 Heat Exchanger Control":  "97f31af0-c291-4b56-af92-c80981dc3b39",
    "RX-202 Level Controller":        "c2aa9f6b-a5ba-4738-ba37-5f5058477156",
    "UT-101 Steam Flow":              "0e3370bc-c2a4-4e82-b4ea-729450a11723",
    "UT-102 CW Return Temp":          "21abd792-a420-45bd-acfb-228e2476a133",
    "UT-103 Air Pressure":            "b3efb3d9-93f1-4105-b761-f93cf44ae901",
    "ESD-001 Reactor Trip":           "2aa89310-54aa-47a1-af86-6d8853b5f16b",
    "ESD-002 Coolant Isolation":      "874587f6-a10d-4b4b-bcd2-d1539a23a2a7",
    "IO-RX-001 AI Cards":             "74e9668c-114a-41bf-be1a-abedbafbf9fd",
    "IO-RX-002 AO Cards":             "60ab0932-f470-4e59-94b0-fefd2bebb1e3",
    "IO-UT-001 DI/DO Cards":          "8a36c968-3094-4759-85cb-6a86794b673e",
    "CM-RX-001 S-Series Controller":  "83cd3c65-0be2-4dd5-9e42-4aea04c8b77b",
    "CM-ESD-001 SIS Controller":      "c50e69f4-3158-403b-83fd-945dae646250",
    "PH-STARTUP-001 Startup Phase":   "b19d6769-48d3-43ae-a0c6-1d7ad04a3aa6",
}
doc_ids = {
    "RX-101 Functional Requirements Spec": "7dc4cdbc-1b9a-45ee-8fc4-2e5025d9376d",
    "RX-101 Software Design Document":     "84cccd69-efd5-472f-ac79-39eeb0fe6a88",
    "RX-101 FAT Protocol":                 "69770592-75d1-4dfa-80f7-f1218e7fcee3",
    "RX-102 Functional Requirements Spec": "b40a723b-61d0-4824-a200-d5d90a4a2508",
    "RX-102 FAT Protocol":                 "b2800223-b01b-469c-91bf-dc14d153070f",
    "ESD-001 Safety Requirements Spec":    "8c8b049b-3249-4f5c-a59c-af5102cd5cb6",
    "ESD-001 FAT Protocol":                "39b27473-3222-449d-8eed-fd871e391cbd",
    "ESD-001 SAT Protocol":                "fbb6090b-067d-452a-ba35-7f2d7fa8368d",
    "Project FAT Plan":                    "dd6c1ccc-601d-4e5d-b08e-fdef2ac3a002",
    "Project SAT Plan":                    "74e1ffd4-c4ff-4791-a301-9f4dcb0f8810",
    "RX-103 Functional Requirements Spec": "65701e34-6cc5-4cad-9e1c-23be65bac419",
    "UT-101 FAT Protocol":                 "e4197957-9878-4fd9-8864-6e756195f0e0",
}

def get_wf(oid):
    d = get(f"/entities/{oid}/workflow")
    if "stage_instances" not in d:
        return None
    return d

def complete_task(oid, task_id):
    put(f"/entities/{oid}/workflow/tasks/{task_id}/complete",
        {"completed_by": "seed", "notes": "Seeded"})

def advance_stage(oid, stage_id):
    post(f"/entities/{oid}/workflow/stages/{stage_id}/advance")

def get_stage(wf, key):
    for s in wf["stage_instances"]:
        if s["stage_key"] == key:
            return s
    return None

def complete_tasks(oid, stage, keys):
    for t in stage["task_instances"]:
        if t["task_key"] in keys:
            complete_task(oid, t["id"])

print("=== Advancing stages ===")

# ESD-001: engineering -> fat_prep -> fat_execution done -> sat_prep active
print("ESD-001 Reactor Trip -> sat_prep...")
oid = obj_ids["ESD-001 Reactor Trip"]
wf = get_wf(oid)
s = get_stage(wf, "engineering")
complete_tasks(oid, s, ["design_review", "config_complete", "code_review"])
advance_stage(oid, s["id"])
wf = get_wf(oid)
s = get_stage(wf, "fat_prep")
complete_tasks(oid, s, ["test_plan", "io_checkout"])
advance_stage(oid, s["id"])
wf = get_wf(oid)
s = get_stage(wf, "fat_execution")
complete_tasks(oid, s, ["fat_run", "punch_closed"])
advance_stage(oid, s["id"])
print("  Done.")

# ESD-002: engineering done, fat_prep partially done
print("ESD-002 Coolant Isolation -> fat_prep (1 task)...")
oid = obj_ids["ESD-002 Coolant Isolation"]
wf = get_wf(oid)
s = get_stage(wf, "engineering")
complete_tasks(oid, s, ["design_review", "config_complete", "code_review"])
advance_stage(oid, s["id"])
wf = get_wf(oid)
s = get_stage(wf, "fat_prep")
complete_tasks(oid, s, ["test_plan"])
print("  Done.")

# RX-102: engineering done, fat_prep active
print("RX-102 Pressure Controller -> fat_prep...")
oid = obj_ids["RX-102 Pressure Controller"]
wf = get_wf(oid)
s = get_stage(wf, "engineering")
complete_tasks(oid, s, ["design_review", "config_complete", "code_review"])
advance_stage(oid, s["id"])
print("  Done.")

# RX-101: engineering 2/3
print("RX-101 Temperature Controller -> engineering (2/3)...")
oid = obj_ids["RX-101 Temperature Controller"]
wf = get_wf(oid)
if wf:
    s = get_stage(wf, "engineering")
    complete_tasks(oid, s, ["design_review", "config_complete"])
print("  Done.")

# UT-101/102: engineering 1/3
for name in ["UT-101 Steam Flow", "UT-102 CW Return Temp"]:
    print(f"{name} -> engineering (1/3)...")
    oid = obj_ids[name]
    wf = get_wf(oid)
    if wf:
        s = get_stage(wf, "engineering")
        complete_tasks(oid, s, ["design_review"])
    print("  Done.")

print("\n=== Evaluating readiness ===")
all_pairs = (
    [(i, "object")   for i in obj_ids.values()] +
    [(i, "document") for i in doc_ids.values()]
)
for eid, etype in all_pairs:
    r = post(f"/entities/{eid}/readiness/evaluate", params={"entity_type": etype})
    if r.status_code == 200:
        d = r.json()
        print(f"  {eid[:8]}... readiness={d['overall_readiness']:.0%}  blockers={len(d['blockers'])}")
    else:
        print(f"  {eid[:8]}... FAILED {r.status_code}: {r.text[:80]}")

print("\n=== All done! ===")
print("Open http://localhost:5174 and select 'Reactor Control Upgrade - Phase 2'")
