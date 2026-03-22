# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Phases 1–5 are complete. V3 gap analysis (2026-03-21) Tier 1 + Tier 2 are complete. Phase 6 (3D cube) is pending Tier 3.

| Phase | Description | Status |
|---|---|---|
| 1 | Backend scaffold — FastAPI, SQLAlchemy models, Alembic migrations | ✅ Complete |
| 2 | CRUD APIs — all entities, routers wired into FastAPI | ✅ Complete |
| 3 | Dependency & Readiness engine — 3-dimensional calculation, blocker explanations, re-evaluation triggers | ✅ Complete |
| 4 | Frontend 2D — Dashboard, Graph View (React Flow), List View, Detail Panel | ✅ Complete |
| 5 | Workflow Designer — Template library, Stage/Task builder (drag-sort), Rule builder, Simulation panel | ✅ Complete |
| V3-T1 | Tier-1 architectural gaps — CBS/ABS/SBS/EBS dimensions, decimal duration/lag (Float), EffortMatrixCell model, WorkCalendar + CalendarException models, object_type generalised (free-text) | ✅ Complete |
| V3-T2 | Tier-2 core features — BR-5.3 effort/duration warnings, reset-overrides endpoint, PATCH task scheduling, WBS Cartesian-product generation, RACI + Resource Assignment matrix views, Deliverable Register view | ✅ Complete |
| V3-T3 | Tier-3 views/reports — PDF/Excel/CSV export, composable dashboard, dependency matrix view, interactive HTML, scenario comparison UI, version report | 🔜 Next |
| 6 | 3D Cube — React Three Fiber, slice views, heatmap overlay | 🔜 After T3 |

**Pending: Supabase database connection.** `backend/.env` DATABASE_URL still points at local Docker PostgreSQL (`localhost:5432`). Update with the Supabase direct connection string when the database password is available. Until then, develop against local Docker — `docker-compose up -d`. Schema is already applied locally.

**Pending: Frontend colour theme alignment.** The current UI uses generic Tailwind colours. The frontend colour scheme must be aligned with the other Prism product suite before release. Obtain the Prism design tokens / brand colours from the team and apply them across Tailwind config and component classes.

## Planned Tech Stack

- **Frontend**: React + TypeScript + Tailwind CSS + React Flow (Phase 4); React Three Fiber added at Phase 6 only
- **Backend**: FastAPI + Python
- **Database**: Supabase (PostgreSQL) — SQLAlchemy + Alembic for schema management, `supabase-py` for Storage and Auth
- **File storage**: Supabase Storage (`evidence` bucket) — see `backend/app/storage.py`
- **State**: React Query + Zustand

## Architecture Overview

The system is a workflow and dependency engine for DeltaV project execution. Everything revolves around **Entities** (Objects and Documents) that have **WorkflowInstances** tracking stage/task progress, and a **ReadinessEngine** that derives readiness from three dimensions.

```
Project → Areas/Units → Objects (IO, CM, EM, Phase, etc.)
                      → Documents (FRS, SDD, FAT, SAT, etc.)
                           ↓
                    WorkflowInstance
                      ├── StageInstances
                      │     └── TaskInstances
                      └── linked to WorkflowTemplateVersion
                           ↓
                    ReadinessEvaluation
                      ├── technical_readiness (tasks complete)
                      ├── document_readiness (mandatory docs approved)
                      └── stage_readiness (dependency rules satisfied)
```

**DependencyRules** connect entities (Object→Object, Object→Document, Document→Stage, Stage→Stage, Test→Document). Deleting a rule must trigger re-evaluation of all affected ReadinessEvaluations.

## Key Invariants (Engine Must Enforce)

1. A StageInstance cannot advance if any entry criterion evaluates false.
2. Object cannot reach FAT Ready if any mandatory linked document is not in Approved state.
3. Object cannot reach SAT Ready if FAT Execution result is not PASS.
4. DependencyRule deletion triggers re-evaluation of all affected ReadinessEvaluations.
5. Template changes propagate to live instances automatically, except fields that have been manually overridden at the instance level. Propagation is logged in the audit trail.
6. Every blocker must carry a human-readable `reason` string.
7. Readiness percentage is always derived/calculated — never manually set.

## Workflow Versioning

- Templates are versioned (e.g. `EM_Standard_v1`, `v2`)
- Instances record the template version they were created from
- Template changes auto-propagate to live instances except for fields overridden at the instance level (`overridden_fields` JSONB column tracks these). Propagation is logged in the audit trail for GMP traceability.

## Build Order

Follow this sequence when implementing:
1. Data models + migrations
2. CRUD APIs (objects, documents, relationships)
3. Workflow templates + versioning
4. Dependency engine + rule evaluation
5. Readiness engine (three-dimensional, with blocker explanations)
6. UI — graph view + detail panels
7. Workflow Designer UI
8. 3D cube (React Three Fiber)

## Readiness API Contract

The readiness endpoint is the most critical API — design the data model around it:

```json
GET /entities/{id}/readiness
{
  "technical_readiness": 0.0,
  "document_readiness": 0.0,
  "stage_readiness": 0.0,
  "overall_readiness": 0.0,
  "ready_for_fat": false,
  "ready_for_sat": false,
  "blockers": [
    {
      "type": "document|dependency|task|stage_gate",
      "entity_id": "string",
      "entity_name": "string",
      "reason": "string",
      "severity": "blocking|warning"
    }
  ],
  "next_action": "string"
}
```

## Implementation Notes

- Design readiness and dependency APIs before CRUD — they drive the data model
- Use a JSON-based rule engine for dependency logic
- Keep workflows versioned from day one
- Separate templates from instances strictly (no shared mutable state)
- Re-evaluate readiness on any state change — consider an event-driven pattern
- Keep the Object entity schema extensible for future Prism/FHX import (auto-populate objects from parsed FHX files)
- React Three Fiber is NOT part of the stack until Phase 6 — do not add it earlier

## MVP Scope

Objects + documents with relationships, hardcoded workflow templates for EM/Phase/Document types, dependency engine with blocker explanations, readiness engine (all three dimensions), 2D graph UI (React Flow), basic 3D cube.

Full Workflow Designer configurability follows MVP validation.
