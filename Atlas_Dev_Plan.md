# DeltaV Project Planner — Full Development Plan

## Executive Summary

A configurable workflow and dependency engine for DeltaV project execution with 3D visualization and document-driven readiness.

\---

## Core Concepts

* Object-centric system (EMs, Phases, Recipes, etc.)
* Documents as active workflow entities (FRS, SDD, FAT, SAT)
* Configurable workflows per object type
* Configurable dependency rules
* Stage-gated project execution
* Graph-first visualization (2D daily use); 3D cube as executive/exploration mode

\---

## Architecture Overview

* Frontend: React + TypeScript + Tailwind + React Flow (Phase 4); React Three Fiber added at Phase 6 only
* Backend: FastAPI + Python
* Database: PostgreSQL (optionally Neo4j later)
* State: React Query / Zustand

\---

## Core Entities

* Project
* Area / Unit
* Object (IO, CM, EM, Phase, etc.)
* Document (FRS, SDD, FAT, SAT etc.)
* WorkflowTemplate
* WorkflowTemplateVersion
* WorkflowInstance
* StageInstance
* TaskInstance
* Relationship
* DependencyRule
* ReadinessEvaluation
* Evidence

\---

## Workflow Model

Each object/document has:

* Stages
* Tasks
* Entry Criteria
* Exit Criteria
* Dependencies
* Evidence Requirements

### Example Stages

* Engineering
* Review
* FAT Prep
* FAT Execution
* SAT Prep
* SAT Execution
* Closeout

### Workflow Versioning

* WorkflowTemplates are versioned (e.g. EM\_Standard\_v1, v2)
* WorkflowInstances record the template version they were created from
* Changing a template does NOT automatically mutate live instances
* A project administrator must explicitly migrate instances to a new template version
* Migration events are logged for GMP change control traceability

\---

## Dependency Types

* Object → Object
* Object → Document
* Document → Stage
* Stage → Stage
* Test → Document (e.g. FAT execution cannot begin until FAT Protocol is in Approved state)

\---

## Key Invariants

Business rules the engine must always enforce:

1. A StageInstance cannot advance to the next stage if any entry criterion evaluates to false.
2. An object cannot reach FAT Ready status if any mandatory linked document is not in an approved state.
3. An object cannot reach SAT Ready status if FAT Execution result is not recorded as PASS.
4. A DependencyRule deletion must trigger re-evaluation of all ReadinessEvaluations for affected entities.
5. WorkflowTemplate changes do not affect existing WorkflowInstances without explicit migration.
6. Every blocker must carry an explanation string suitable for display to the user.
7. Readiness percentage must be derived, never manually set.

\---

## Readiness Model

Three-dimensional readiness per entity:

* **Technical Readiness** — object workflow stages and tasks complete
* **Document Readiness** — all mandatory linked documents at required state
* **Stage Readiness** — all dependency rules and entry criteria satisfied

Overall Readiness = conjunction of all three.

Each entity must expose:

* blockers (list with explanation per blocker)
* readiness % per dimension
* overall readiness %
* next recommended action

\---

## API Design

### Projects

```
GET  /projects
POST /projects
GET  /projects/{id}
```

### Objects

```
GET  /objects?project\_id=\&type=\&status=
POST /objects
GET  /objects/{id}
PUT  /objects/{id}
```

### Documents

```
GET  /documents?project\_id=\&type=\&status=
POST /documents
GET  /documents/{id}
PUT  /documents/{id}
```

### Workflow Templates

```
GET  /workflow-templates
POST /workflow-templates
GET  /workflow-templates/{id}
POST /workflow-templates/{id}/versions
GET  /workflow-templates/{id}/versions/{version}
```

### Workflow Instances

```
POST /entities/{id}/workflow          — instantiate workflow on an object or document
GET  /entities/{id}/workflow          — get live workflow state
PUT  /entities/{id}/workflow/stages/{stage\_id}/advance
```

### Dependencies

```
GET  /dependency-rules?template\_id=
POST /dependency-rules
DELETE /dependency-rules/{id}         — triggers re-evaluation of affected readiness
GET  /entities/{id}/dependencies      — what this entity depends on
GET  /entities/{id}/blocks            — what this entity is blocking
```

### Readiness (Critical — drives data model decisions)

```
GET  /entities/{id}/readiness
  Response:
  {
    technical\_readiness: float,
    document\_readiness: float,
    stage\_readiness: float,
    overall\_readiness: float,
    ready\_for\_fat: bool,
    ready\_for\_sat: bool,
    blockers: \[
      {
        type: "document" | "dependency" | "task" | "stage\_gate",
        entity\_id: string,
        entity\_name: string,
        reason: string,
        severity: "blocking" | "warning"
      }
    ],
    next\_action: string
  }

GET  /entities/{id}/blockers          — list of blocking entities with explanations
GET  /projects/{id}/readiness-summary — rollup across all units and objects
GET  /projects/{id}/fat-readiness     — all objects, their FAT readiness, blockers
GET  /projects/{id}/sat-readiness     — all objects, their SAT readiness, blockers
```

### Evidence

```
POST /tasks/{id}/evidence
GET  /tasks/{id}/evidence
DELETE /evidence/{id}
```

\---

## UI Structure

### Main Areas

* Dashboard
* Graph View (primary daily-use visualization — React Flow)
* 3D Project Space (exploration / executive mode — Phase 6)
* Slice View
* Object Detail
* Document Detail
* Workflow Designer

\---

## Graph View (Primary Visualization)

* Nodes = objects and documents
* Edges = dependencies and relationships
* Color = status (green / amber / red / grey)
* Click node → detail panel slides in from right
* Toggle dependency lines on/off
* Filter by: object type, status, stage, unit
* "Why is this blocked?" button on red nodes

\---

## 3D Cube Model (Phase 6 — Exploration Mode)

Axes:

* X: System (Area → Unit → Object)
* Y: Stage (Design → FAT → SAT)
* Z: Dependency class (Technical / Docs / Test / Approval)

Features:

* rotate / zoom
* slice views (slice by unit, by stage, by dependency class)
* dependency lines on demand
* heatmap overlay (red clusters = bottlenecks)

Note: 3D is for insight and presentation. Graph view is for execution.

\---

## Workflow Designer

### Components

* Template Library (browse by object type, with versioning)
* Stage Builder (drag/reorder stages, mark optional/mandatory)
* Task Builder (add tasks within stages)
* Rule Builder (no-code entry/exit criteria using dropdowns + conditions)
* Relationship Builder (define required document link types per object type)
* Simulation Panel (test rule logic against a hypothetical object state)
* Project Override Editor (project-specific modifications on top of base templates)

\---

## Development Phases

### Phase 1 — Core Backend

* Data models and migrations
* CRUD APIs for all core entities
* Relationship model

### Phase 2 — Workflow Engine

* WorkflowTemplate + versioning
* WorkflowInstance creation from template
* Stage and task lifecycle logic

### Phase 3 — Dependency \& Readiness Engine

* DependencyRule evaluation
* Blocker calculation with explanations
* Readiness % per dimension
* Re-evaluation triggers on rule/state changes

### Phase 4 — Frontend (2D)

* Dashboard
* Object and document detail views
* Graph view (React Flow)
* Matrix / list fallback view

### Phase 5 — Workflow Designer

* Template library UI
* Stage/task/rule builders
* Simulation panel
* Project override editor

### Phase 6 — 3D Visualization

* React Three Fiber added to stack here (not before)
* Cube rendering
* Slice views
* Heatmap overlay
* Dependency line toggles

\---

## MVP Scope

* Objects + documents with relationships
* Hardcoded-but-sensible workflow templates (EM, Phase, Document) to validate data model
* Dependency engine with blocker explanations
* Readiness engine (all three dimensions)
* 2D graph UI
* Basic cube (can be simplified for MVP)

Note: Full workflow configurability (Workflow Designer) follows MVP validation.

\---

## Future Enhancements

* Prism / FHX import (auto-populate project object list from parsed FHX)
* AI assistant / Mossi integration ("show EMs blocking SAT", natural language queries)
* Advanced reporting and milestone dashboards
* Scheduling layer (link readiness state to target dates)
* Punch item and deviation tracking

\---

## Build Order

1. Data model + migrations
2. CRUD APIs (objects, documents, relationships)
3. Workflow templates + versioning
4. Dependency engine + rule evaluation
5. Readiness engine (three-dimensional, with blocker explanations)
6. UI — graph view + detail panels
7. Workflow Designer UI
8. 3D cube

\---

## Notes for Claude Code

* Prioritise backend first; readiness and dependency APIs are the most important — design these before CRUD
* Use JSON-based rule engine for dependency logic
* Keep workflows versioned from day one; retrofit is painful
* Separate templates from instances strictly
* Every blocker must include a human-readable explanation string
* Readiness must always be derived/calculated, never manually overridden
* Re-evaluate affected readiness on any state change (consider event-driven pattern)
* Prism integration is a future enhancement but keep object import interface in mind when designing the Object entity schema

