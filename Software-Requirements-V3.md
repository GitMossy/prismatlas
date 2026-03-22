# 4D Object-Oriented Project Management Software

## Software Requirements Specification

**Version:** 3.0
**Date:** 2026-03-21
**Domain:** Large-Scale Industrial Automation Projects (ISA-88/S88, ISA-95, IEC 61131)

\---

# Prompt

Read this file and combine the information with your knowledge about project management software to write, in markdown format, a requirements document for project management software that will make it easier to manage a large automation project. Instead of creating a long list or tree of tasks to manage the project activities, this new software will support 4D object oriented scheduling where:

1. Project scope is divided into Areas, groups, or systems.
2. Each Area includes a set of Classes and Items that are needed in that Area must be delivered by the end of the project.
3. Classes can have a multiple sets of instances that are created from the class and a set of instances is included in the Area or Group where needed.
4. Each Area, Group, Class, Item, and Set of Instances has a Type and all all schedule objects of a given Type share a set of attributes.
5. Each type has a workflow associated with it and the workflow is repeated for each schedule object of that type.
6. Each step in a workflow can produce a deliverable.
7. Each step in a workflow has a calendar time duration (elapsed time) and an effort (person hours or days of effort).
8. Internal Links are defined between steps in the workflow and/or deliverables from the workflow.
9. External links can be defined in the schedule between objects.

What makes the scheduling easier is:

1. It is modular. Workflows, deliverables, durations, and links can be defined one type at a time.
2. All types are reusable so effort put into defining the details of the Type does not need to be repeated for every object of that Type. For example, Internal Links are automatically updated in each new object created from a Type.
3. It is class based. Changes to the Type are automatically updated in all schedule objects assigned to that type.
4. It is multi-dimensional. Many different project management tools, reports, and dashboards can be achieved just be looking at a spreadsheet or table created from one dimensions for rows and another dimension for columns.

## 1\. Purpose and Problem Statement

### 1.1 Problem

Traditional project management tools (Microsoft Project, Primavera P6, Jira) model work as a one-dimensional list or tree of tasks — a Work Breakdown Structure (WBS). On large automation projects involving hundreds of equipment items, software classes, and multi-phase workflows, this approach produces schedules with thousands of individually-authored tasks, each manually linked. The consequences are quantifiable:

* A 500-equipment automation project with a 6-step workflow and 3 deliverables per step generates approximately 500 × 6 = 3,000 tasks and 500 × 18 = 9,000 deliverables. In a flat WBS every task and every link is created and maintained by hand.
* A single workflow change (e.g., inserting a peer-review gate) requires editing every affected task individually — on the order of 500 manual edits with associated re-linking.
* Resource loading, cross-area dependency analysis, and status reporting each require a separate view or report that must be manually kept consistent with the schedule.

### 1.2 Solution Overview

This software replaces flat task lists with a **multi-dimensional, class-based scheduling model** — referred to as 4D Object-Oriented Scheduling. The core idea, drawn from the DART framework (Deliverables (CBS/DBS) × Activities (ABS) × Resources (RBS) × Time (TBS)) and 4D-WBS methods, is:

* **Scope** is decomposed along multiple independent dimensions (Where, What, How, Who, When) rather than a single tree.
* **Types** serve as reusable templates that define attributes, workflows, deliverables, durations, and internal links once. Every schedule object assigned to a Type inherits and stays synchronized with that definition.
* **Views** are generated dynamically by selecting any two dimensions for rows and columns of a matrix, producing Gantt charts, resource-loading histograms, status matrices, and assignment summaries from a single underlying model.

The practical effect demonstrated in field use: a 1,200-task Primavera P6 schedule for a factory automation project was generated in a single day from a populated WBS matrix, compared to weeks of manual entry.

### 1.3 Key Differentiators vs. Existing Tools

|Capability|MS Project / P6|Jira / Azure DevOps|This Software|
|-|-|-|-|
|Schedule structure|1D task tree (WBS)|Flat backlog + sprints|Multi-dimensional hierarchies <br>(EBS/ZBS × CBS × ABS × RBS × TBS)|
|Reuse mechanism|Copy/paste tasks|Issue templates (no link propagation)|Type system with inheritance; changes propagate to all instances|
|Workflow definition|Manual per-task predecessors|Board columns (no per-item effort/duration)|Typed workflows with steps, durations, effort, deliverables, and internal links — cloned automatically|
|View generation|Single Gantt + manual reports|Board + backlog + limited reports|Dynamic matrix pivot: any dimension × any dimension|
|Typical task count for 500-item project|3,000+ manually created|3,000+ tickets|\~6 Type definitions → 3,000 tasks auto-generated|
|Impact of workflow change|\~500 manual edits|\~500 ticket edits|1 Type edit → 500 instances updated|

\---

## 2\. Scope and Applicability

### 2.1 Target Project Characteristics

The software is designed for projects that share these traits:

* **Repetitive structure**: Many items of a few types, each following the same lifecycle (e.g., 20 control module classes, 5 unit module classes, 30 phase classes and 500 instances of these classes spread across 10 units on an S88 batch plant)
* **Multi-area deployment**: The same class of deliverable is instantiated across multiple physical areas, process units, or system zones.
* **Phased workflows**: Each item progresses through a defined sequence of engineering activities (specify, design, code, test, integrate, commission) with measurable deliverables at each step.
* **Cross-cutting dependencies**: In addition to internal links between tasks within an object, milestones in one area or system depend on deliverables from another (e.g., a batch sequencer cannot be integration-tested until all equipment modules in its unit are factory-tested).

### 2.2 Industry Alignment

The data model aligns with established industrial standards:

* **ISA-88 (S88)** physical model: Enterprise → Site → Area → Process Cell → Unit → Equipment Module → Control Module. The software's Zone/Area hierarchy maps directly to this structure.
* **ISA-95** functional hierarchy for integrating control-system deliverables with MES and ERP layers.
* **IEC 61131-3** program organization units (Programs, Function Blocks, Functions) which map to the Class/Instance model for PLC and DCS software.
* **IEEE 15288 / 12207** system and software lifecycle processes, which provide a basis for workflow step definitions.
* 

\---

## 3\. Definitions and Concepts

### 3.1 Multi-Dimensional Breakdown Structures

The schedule model is built on independent, hierarchical breakdown structures — each representing one dimension of the project. These are derived from the DART framework and 4D-WBS methodology:

|Dimension|Breakdown Structure|Abbreviation|Description|Typical Source Document|
|-|-|-|-|-|
|**Where**|Zone / System Breakdown Structure|ZBS/EBS|Physical or logical scope divisions: areas, process units, equipment groups.|Process Flow Diagrams (PFDs), P\&IDs, Physical Architecture Drawings|
|**What**|Configuration Breakdown Structure<br><br><br><br><br>Deliverable Breakdown Structure|CBS<br><br><br><br><br><br><br>DBS|Produced Artifacts ( software classes, hardware assemblies)<br><br>Deliverable components: documents.|Software Architecture Documents (SAD), Software Bills of Material (SBOM)|
|**How**|Activity Breakdown Structure|ABS|Engineering activities organized as workflows: Stage → Task → Step.|Lifecycle procedures, quality plans|
|**Who**|Resource / Organization Breakdown Structure|RBS|People and teams: Company → Group → Person.|Org charts, RACI matrices|
|**When**<br><br>**How Long**|Time Breakdown Structure|TBS|Calendar hierarchy: Year → Quarter → Month → Week → Day; or Sprint cadence.|Project calendar, sprint schedule|
|**Why**|Value Breakdown Structure|VBS|Business value contributed by each deliverable, enabling scope trade-off decisions.|Business case, ROI models|
|**Which**|System Breakdown Structure|SBS|System Components used to run the CBS items on the ZBS/EBS|Network Diagrams|

### 3.2 Core Schedule Objects

**Area (or Group, or Zone):** A node in the EBS/ZBS.  It represents a group, not a leaf on the tree.  Represents a physical location, process unit, or logical system grouping. Each Area contains the set of Classes, Items, and Instance Sets that must be delivered for that portion of the project.

**Class:** A reusable design artifact in the CBS (e.g., a Motor Control class, a PID Loop class, a phase class). A Class is defined once and instantiated multiple times.

**Item:** A singular deliverable component in the CBS that is not instantiated (e.g., a system-wide configuration file, a network architecture document).

**Set of Instances:** A group of instances created from a Class and deployed into a specific Area or Unit. For example, Area "Reactor-01" may contain a set of 12 instances of the "ValveControl" class. The set is the schedulable unit — the workflow applies to the set, not to each individual instance, unless the Type specifies otherwise.

**Type:** A template that defines the shared characteristics of schedule objects. Every Area, Class, Item, and Instance Set is assigned exactly one Type. The Type specifies: custom attributes and their data types, the workflow (ordered steps with durations, effort, and deliverables), internal links between workflow steps, and default values for scheduling parameters.

### 3.3 Workflow Concepts

**Workflow:** An ordered sequence of Steps associated with a Type.  Typically, these are the steps needed to produce an object of that type. When a schedule object is created and assigned a Type, the workflow is cloned into a concrete set of tasks for that object.  Workflow steps are selected from the ABS.

**Step:** A single unit of work within a workflow selected from the ABS. Each step has a name and description, a calendar duration (elapsed days), an effort estimate (person-hours or person-days), zero or more deliverables produced, and attributes inherited from the Type (which can be overridden per-instance).

**Deliverable:** A tangible output of a Step (document, test report, redlines, completed checklist, signed approval). Deliverables can participate in dependency links.  A production of a deliverable follows its own workflow.

**Internal Link:** A dependency defined within a workflow template — e.g., "Code" cannot start until "Spec.deliverable" is approved. Internal links are automatically replicated in every instance of the workflow.

**External Link:** A dependency defined between schedule objects — e.g., "Area-01.IntegrationTest" depends on "Area-02.EquipmentModule.FactoryTest.complete". External links are defined explicitly at the schedule level, not within the Type template.

\---

## 4\. Functional Requirements

### 4.1 Multi-Dimensional Hierarchy Management

**FR-4.1.1 Hierarchy CRUD.** The system shall support creation, reading, updating, and deletion of hierarchical trees for each breakdown structure dimension (ZBS, CBS, ABS, RBS, OBS, TBS). Each tree shall support unlimited nesting depth.

**FR-4.1.2 Drag-and-Drop Restructuring.** Users shall be able to restructure hierarchies by dragging nodes between parents. The system shall update all affected schedule objects, links, and views within 2 seconds for trees up to 1,000 nodes.

**FR-4.1.3 Multi-Parent Assignment.** A CBS item (Class or Item) shall be assignable to multiple EBS/ZBS nodes (Areas) via Instance Sets. The system shall track which instances belong to which Area while maintaining the Class-level Type definition.

**FR-4.1.4 Hierarchy Import.** The system shall import hierarchy trees from CSV and XML files, with field mapping configuration. Target import sources include Primavera P6 XML (XER), and Microsoft Project XML.

**FR-4.1.5 Hierarchy Versioning.** Each hierarchy shall maintain a version history. Users shall be able to compare two versions and see additions, deletions, and moves.

### 4.2 Type System

**FR-4.2.1 Type Definition.** A Type shall consist of a unique name and version identifier, a parent Type (for inheritance), a set of custom attributes with data types (text, numeric, enumeration, date, boolean, reference), a workflow template, and a set of internal links.

**FR-4.2.2 Type Library.** Types shall be organized in a library that is filterable by category (Area Types, Class Types, Item Types, Instance Set Types). The library shall support import/export for reuse across projects.

**FR-4.2.3 Type Inheritance.** A child Type shall inherit all attributes, workflow steps, and internal links from its parent Type. The child may add attributes, add steps, override default durations/effort, and add internal links. It shall not remove inherited attributes or steps (to preserve structural consistency); instead, inherited steps may be marked as "skipped" with zero duration.

**FR-4.2.4 Propagation on Type Edit.** When a Type definition is modified (attribute added, step duration changed, internal link added), the system shall propagate the change to all schedule objects currently assigned to that Type. Propagation rules:

|Change|Propagation Behavior|
|-|-|
|New attribute added|Added to all instances with default value|
|Attribute default changed|Updated only on instances where value was not manually overridden|
|Step added to workflow|New task inserted in all instance workflows at correct position|
|Step duration changed|Updated only on instances where duration was not manually overridden|
|Internal link added|Link added to all instance workflows|
|Internal link removed|Link removed from all instance workflows (with confirmation)|

**FR-4.2.5 Override Tracking.** The system shall track which attribute values and durations have been manually overridden at the instance level. Overridden values shall be visually distinguished (e.g., bold or colored) and shall not be affected by Type propagation unless the user explicitly requests a "reset to Type default" operation.

**FR-4.2.6 Type Versioning.** Types shall be versioned. When a Type is modified, the system shall create a new version. Schedule objects may reference a specific Type version or "latest." A report shall list all objects not yet updated to the latest Type version.

### 4.3 Workflow Engine

**FR-4.3.1 Visual Workflow Editor.** The system shall provide a flowchart-style editor for defining workflow templates within a Type. Users shall drag-and-drop steps, connect them with links, and define parallel and sequential paths.

**FR-4.3.2 Step Properties.** Each workflow step shall have configurable properties: name, description, planned calendar duration (elapsed days — decimal, minimum granularity 0.5 days), planned effort (person-days — decimal, minimum granularity 0.5 days), a list of deliverables (each with name, type/format, and approval requirements, and a link to a template for that deliverable), responsible role (reference to RBS), and custom attributes (inherited from Type, overridable).

**FR-4.3.3 Effort Estimation Matrix.** The system shall support an Effort Matrix where rows represent Types and columns represent workflow steps (activities). Each cell contains a base effort value. Effort for a specific instance may be scaled by a complexity multiplier attribute defined on the Type (e.g., Low = 0.5×, Medium = 1.0×, High = 2.0×). This matrix approach enables rapid estimation: define effort per Type × Activity cell once, apply automatically to all instances.

**FR-4.3.4 Internal Link Types.** Internal links within a workflow shall support standard dependency types: Finish-to-Start (FS — default), Start-to-Start (SS), Finish-to-Finish (FF), and Start-to-Finish (SF). Each link shall support a lag (positive only, in days - decimal).

**FR-4.3.5 Workflow Instantiation.** When a schedule object is created and assigned a Type, the system shall automatically generate a concrete set of tasks by cloning the Type's workflow. Each generated task shall inherit step properties, be linked according to internal link definitions, and be assigned to the Area containing the schedule object.

**FR-4.3.6 Deliverable Tracking.** Each deliverable shall have a status based on a defined workflow for that deliverable type (Not Started, In Progress, In Review, Approved, Rejected) and an actual completion date. Deliverable status shall drive dependency logic: a Finish-to-Start link to a deliverable shall not allow the successor to start until the deliverable reaches  a terminal step in the workflow (e.g. "Approved" status) (configurable per link).

### 4.4 Scheduling and Task Generation

**FR-4.4.1 Automated WBS Generation.** The system shall generate a flat task list (WBS) by computing the Cartesian product of selected dimensions. For example: Tasks = {Instance Sets in selected Areas} × {Steps in each Instance Set's Type workflow}. The generated WBS shall be exportable to Primavera P6 (XER/XML), Microsoft Project (XML/MPP via API), and CSV/Excel.

**FR-4.4.2 Forward and Backward Pass.** The system shall compute Early Start, Early Finish, Late Start, Late Finish, and Total Float for each task using both internal and external links. The scheduling algorithm shall use the Critical Path Method (CPM) with calendar-aware date arithmetic (respecting working days, holidays, and resource calendars).

**FR-4.4.3 Critical Path Identification.** The system shall identify and highlight the critical path (Total Float = 0). Near-critical paths (Total Float ≤ user-defined threshold, default 5 days) shall also be identifiable.

**FR-4.4.4 Resource Assignment and Leveling.** Users shall assign resources (from RBS) to workflow steps. The system shall compute resource loading (person-hours per time period per resource) and identify over-allocations. Optional automatic resource leveling shall delay non-critical tasks to resolve over-allocations while minimizing project duration increase.

**FR-4.4.5 Baseline Management.** The system shall support multiple named baselines. A baseline captures a snapshot of all task dates, durations, effort, and links at a point in time. Earned Value metrics (PV, EV, AC, SPI, CPI, EAC, ETC) shall be computable against any baseline.

**FR-4.4.6 What-If Scenarios.** Users shall be able to create scenario branches (copies of the current schedule) to evaluate alternatives — for example, adding resources to a critical-path area, deferring a low-value scope area (using VBS data), or changing a Type's workflow. Scenarios shall be comparable side-by-side with metrics: total duration delta, cost delta, and resource peak delta.

### 4.5 External Links and Cross-Object Dependencies

**FR-4.5.1 External Link Definition.** Users shall define dependency links between any two schedule objects (or specific steps/deliverables within their workflows) across Areas, Classes, or Instance Sets. External links shall support the same dependency types and lag as internal links (FS, SS, FF, SF).

**FR-4.5.2 Link Visualization.** External links shall be displayed on: the Gantt chart as connecting lines between bars, a dedicated dependency matrix (rows = predecessors, columns = successors), and a network diagram (nodes = schedule objects, edges = links).

**FR-4.5.3 Circular Dependency Detection.** The system shall detect circular dependencies in real-time as links are added and prevent their creation with a clear error message identifying the cycle path.

**FR-4.5.4 Link Templates.** For recurring cross-object dependency patterns (e.g., "every EquipmentModule.FactoryTest must finish before the containing Area.IntegrationTest starts"), the system shall support link templates that are automatically applied when new objects are added to an Area.

### 4.6 Multi-Dimensional Views and Reports

The following views are generated by:

1. Selecting a breakdown structure dimension for rows and one for columns,
2. Optionally select a third dimension to color-code the cells in the matrix.
3. Optionally select an item in a 4th dimension as a filter to select a slice through the multi-dimensional object to view on the matrix.

For each of the selected dimensions for rows and columns, the user can zoom in or out through the levels in the hierarchy for that dimension to provide a wider or narrower view into the project.  This is the primary mechanism for collapsing the 4D model into actionable 2D representations.

**FR-4.6.1 Standard View Matrix.**

|View Name|Row Dimension|Column Dimension|Cell/Color Dimension|Purpose|
|-|-|-|-|-|
|Task Status Matrix|CBS (Classes/Items)|ABS (Workflow Steps)|Status (color)|Progress tracking — which items are at which stage|
|Gantt Chart|EBS/ZBS (Areas) or CBS|Time|RBS (color)|Traditional time-based schedule view|
|Resource Loading|RBS (Resources)|Time|Effort (heatmap)|Identify over/under-allocation per period|
|Resource Assignment|RBS (Resources)|CBS (Deliverables)|% Allocation|Balance workload across deliverables|
|Area Heatmap|Types|EBS/ZBS (Areas)|Complexity (color)|Risk identification — which areas have the most complex items|
|Deliverable Register|CBS or DBS|ABS (workflow Steps)|Deliverable Status|Track document/artifact completions|
|Resource Allocation|ABS (Workflow steps)|Time|RBS (color)|Resource Scheduling|
|RACI Chart|RBS (Resources)|ABS (Workflow Steps)||Responsibility|

**FR-4.6.2 Custom Pivot Views.** In addition to the standard views, users shall be able to create custom views by:

1. Selecting a breakdown structure dimension for rows and one for columns,
2. Select a metric or attribute for cell values (count, sum of effort, average duration, status, custom attribute)
3. Optionally select a third dimension to color-code the cells in the matrix.
4. Optionally select an item in a 4th dimension as a filter to select a slice through the multi-dimensional object to view on the matrix.

Custom views shall be saveable and shareable.

**FR-4.6.3 Area/Zone Diagrams.** The system shall support associating a graphical layout diagram (uploaded image or SVG) with a EBS/ZBS level. Schedule objects in that zone shall be overlaid on the diagram with color-coded status indicators — providing the "drawing accompanying the schedule" identified as essential for construction and commissioning phases.

**FR-4.6.4 Dashboard Composition.** Users shall compose dashboards from multiple views, charts, and KPI widgets. Standard KPIs shall include: overall percent complete (by task count and by effort), SPI and CPI (when baseline is set), tasks completed this period vs. planned, critical path length (days), resource utilization (% of available capacity), and deliverables pending approval.

**FR-4.6.5 Export Formats.** All views shall be exportable to Excel (.xlsx with formatting preserved), PDF (for print-quality reports), CSV (for data interchange), Primavera P6 XER/XML (for WBS and Gantt), Microsoft Project XML, and interactive HTML (for stakeholder distribution).

### 4.7 Sprint / Agile Overlay (4th Dimension)

For projects using iterative delivery (common in automation software development), the system shall support an optional sprint-based overlay on the schedule.

**FR-4.7.1 Sprint Definition.** Sprints are fixed-duration time boxes (typically 4-6 weeks) organized in a Sprint hierarchy: Release (Epic) → Sprint.
Sprints are sequential blocks of time overlayed on the TBS and become an alternate measure of a block of time in addition to the standard years, quarters, months, weeks, and days.
Each sprint has a capacity (total person-hours available from the makeup of the team assigned to that sprint).

**FR-4.7.2 Sprint Assignment.** Schedule object workflow steps (tasks) shall be assignable to sprints. The system shall show sprint backlog (tasks assigned to a sprint), sprint burndown (effort remaining vs. time), and velocity tracking (effort completed per sprint, rolling average).

**FR-4.7.3 Sprint Teams.** A sprint Team is defined as an RBS group, and . The system shall support this mapping as a named view configuration.

\---

## 5\. Data Integrity and Business Rules

**BR-5.1 Type Assignment Required.** Every schedule object (Area, Class, Item, Instance Set) shall have exactly one Type assigned before it participates in scheduling.

**BR-5.2 Workflow Completeness.** A Type's workflow shall have at least one step. A step with zero duration and zero effort is permitted (for milestone or gate steps).

**BR-5.3 Duration vs. Effort Consistency.** The system shall warn when effort exceeds duration × available resources for a step (indicating an under-staffed task) or when duration greatly exceeds effort ÷ assigned resources (indicating a potentially padded estimate). Warning thresholds shall be configurable (default: warn if ratio deviates >50% from expected).

**BR-5.4 External Link Integrity.** When a schedule object is deleted, all external links referencing it shall be flagged for user review. Deletion shall not proceed until links are reassigned or confirmed for removal.

**BR-5.5 Instance Set Cardinality.** An Instance Set shall record the count of instances it represents. Effort for the set may be scaled by this count (configurable per Type: linear scaling, square-root scaling, or fixed).

\---

## 6\. Integration Requirements

### 6.1 Import / Export

|System|Import|Export|Format|
|-|-|-|-|
|Microsoft Project|Task list, resources, links|Generated WBS, tasks, links|XML, OOXML (.mpp via API)|
|Excel|Hierarchy trees, effort matrices, attribute data|All views, reports, matrices|.xlsx|

### 6.2 API

**FR-6.2.1** The system shall provide a RESTful API and optionally a GraphQL endpoint for all CRUD operations on schedule objects, Types, links, and views.

**FR-6.2.2** The API shall support bulk operations: create/update up to 10,000 objects in a single request (for initial data loads and integrations).

**FR-6.2.3** Webhook notifications shall be available for events: task status change, deliverable approved, critical path change, resource over-allocation detected.

### 6.3 Query Language

**FR-6.3.1** The system shall support a structured query language for traversing the multi-dimensional model. Example queries: "Find all Instance Sets in Area 'Reactor-01' where Type = 'ValveControl' and Step 'Code' status = 'In Progress'" or "Find all external links where predecessor Area ≠ successor Area (cross-area dependencies)."

\---

## 7\. Non-Functional Requirements

### 7.1 Performance

|Metric|Target|
|-|-|
|Maximum schedule objects per project|50,000|
|Maximum concurrent tasks (generated)|200,000|
|Schedule recalculation (CPM) time|< 5 seconds for 50,000 tasks|
|Type propagation (edit → all instances updated)|< 10 seconds for 1,000 instances|
|View rendering (matrix pivot)|< 3 seconds for 10,000 cells|
|API bulk create throughput|≥ 1,000 objects/second|

### 7.2 Usability

**NFR-7.2.1** Web-based UI accessible from modern browsers (Chrome, Edge, Firefox — latest 2 versions). No desktop installation required.

**NFR-7.2.2** Drag-and-drop interaction for hierarchy management, workflow editing, resource assignment, and sprint planning.

**NFR-7.2.3** Keyboard shortcuts for common operations (navigate hierarchy, change status, add link).

**NFR-7.2.4** Undo/redo for all user actions (minimum 50-step history).

### 7.3 Security and Access Control

**NFR-7.3.1** Role-based access control (RBAC) with roles: Project Admin, Planner, Team Lead, Team Member, Viewer.

**NFR-7.3.2** Area-level permissions: users may be granted read/write access to specific Areas, restricting their visibility and edit capability.

**NFR-7.3.3** Audit log of all changes to schedule objects, Types, and links — including who, when, old value, and new value.

### 7.4 Data Management

**NFR-7.4.1** Automatic backup at configurable intervals (default: every 4 hours).

**NFR-7.4.2** Project archive/restore capability.

**NFR-7.4.3** Multi-project support: a single deployment shall host multiple independent projects with a shared Type library.

\---

## 8\. Example Workflow: S88 Batch Automation Project

This section illustrates how the software models a real scenario.

**Project context:** Automate a batch chemical plant with 4 process areas, \~200 equipment modules (valves, motors, PID loops, discrete I/O), organized per ISA-88.

**Step 1 — Define the EBS/ZBS (Where):**

```
Plant
├── Area-01: Reactor Section
├── Area-02: Distillation
├── Area-03: Utilities
└── Area-04: Packaging
```

**Step 2 — Define the CBS (What) with Types:**

```
Type: ControlModClass  (Class type, complexity: Low/Med/High)
Type: EMModClass       (Class type, complexity: Low/Med/High)
Type: UnitClass        (Class type, complexity: Med/High)
Type: PhaseClass       (Class type, complexity: High)
Type: HMIScreen        (Item type, complexity: Med/High)
Type: SystemDocument   (Item type, complexity: Low/Med)
```

**Step 3 — Define Workflows per Type using elements in the ABS (How):**

```
Type: ValveControl
  Workflow:
    1. Specify   → Deliverable: Spec Document    (3d elapsed, 16h effort)
    2. Design    → Deliverable: Design Document   (2d elapsed, 12h effort)
    3. Code      → Deliverable: Source Code        (3d elapsed, 20h effort)
    4. Unit Test → Deliverable: Test Report        (2d elapsed, 12h effort)
    5. FAT       → Deliverable: FAT Certificate    (1d elapsed, 8h effort)
    6. SAT       → Deliverable: SAT Certificate    (1d elapsed, 8h effort)
  Internal Links:
    Specify.complete → Design.start (FS)
    Design.complete → Code.start (FS)
    Code.complete → UnitTest.start (FS)
    UnitTest.complete → FAT.start (FS, +2d lag for test-bed availability)
    FAT.complete → SAT.start (FS)
  Effort Scaling by Complexity:
    Low: 0.6×,  Med: 1.0×,  High: 1.8×
```

**Step 4 — Assign Instance Sets to Areas/Units:**

|Area|Class|Instance Count|Complexity|
|-|-|-|-|
|Reactor Section|ControlMod|45|Med|
|Reactor Section|UnitClass|12|High|
|Reactor Section|PhaseClass|18|High|
|Distillation|ControlMod|60|Low|
|Distillation|UnitClass|22|Med|
|Utilities|PhaseClass|35|Low|
|Utilities|UnitClass|8|Med|
|Packaging|ControlMod|20|Med|
|Packaging|PhaseClass|6|High|

**Step 5 — Define External Links:**

```
Each Area.AllEquipmentModules.FAT.complete → Area.IntegrationTest.start (FS)
Area-01.SequenceModule.Code.complete → Area-01.IntegrationTest.start (FS)
All Areas.IntegrationTest.complete → SystemAcceptanceTest.start (FS)
```

**Step 6 — Generate Schedule:**

The system computes the Cartesian product: 9 Instance Sets × 6 workflow steps = 54 task groups (each group representing the work for one Instance Set at one workflow step). With internal and external links resolved, the CPM algorithm produces early/late dates, critical path, and float values. Total generated tasks: \~226 (9 sets × 6 steps × \~4 sub-tasks average). Total effort: computed automatically from effort matrix × complexity × instance count.

**Result:** A fully-linked, resource-loadable schedule produced from 6 Type definitions, 9 Instance Set assignments, and 5 external links — rather than hundreds of manual task entries.

\---

## 9\. Implementation Roadmap

### Phase 1 — MVP (Months 1–4)

Core data model (hierarchies, Types, schedule objects), Type library with CRUD and basic inheritance, workflow editor with step properties and internal links, automated task generation (Cartesian product), basic matrix views (Task Status, Gantt), and Excel/CSV export.

**Exit criteria:** A planner can define Types, populate Areas with Instance Sets, and generate a schedule with correct internal links. The schedule can be exported to P6 or MS Project for validation.

### Phase 2 — Scheduling Engine (Months 5–7)

CPM forward/backward pass with calendar support, external link management with circular-dependency detection, resource assignment and loading histograms, baseline capture and earned-value metrics, and P6 XER and MS Project XML bidirectional import/export.

**Exit criteria:** The system produces a fully-scheduled, resource-loaded plan with critical path identification, validated against P6 output for a 1,000+ task project.

### Phase 3 — Advanced Views and Collaboration (Months 8–10)

Custom pivot views with save/share, dashboard composition, zone diagram overlays, sprint/agile overlay (HAVSTS), role-based access control, audit logging, and REST API with webhooks.

**Exit criteria:** A multi-user team can collaboratively manage a 5,000+ object project with dashboards, sprint tracking, and external system integration.

### Phase 4 — Intelligence and Scale (Months 11–13)

What-if scenario branching, effort estimation assistance (historical data analysis, complexity-based scaling recommendations), link templates for automated cross-area dependency generation, bulk import wizards for Cradle and legacy systems, and performance optimization for 50,000+ object projects.

\---

## 10\. Glossary

|Term|Definition|
|-|-|
|ABS|Activity Breakdown Structure — hierarchy of engineering activities (Stage → Task → Step)|
|Area|A node in the ZBS representing a physical or logical scope division|
|Class|A reusable design artifact in the CBS that can be instantiated multiple times|
|CPM|Critical Path Method — scheduling algorithm computing earliest/latest dates and float|
|DART|Deliverables × Activities × Resources × Time — the four scheduling dimensions|
|DBS|Document or Deliverable Breakdown Structure.  Deliverable/Document categories associated with individual steps in a workflow.|
|EBS|Equipment Breakdown Structure. Alternate or supplement for ZBS depending on the items selected for the hierarchy.  Corresponds to the S88 equipment hierarchies.|
|External Link|A dependency between two different schedule objects|
|Instance Set|A group of instances of a Class deployed to a specific Area|
|Internal Link|A dependency defined within a Type's workflow template, auto-replicated to all instances|
|Item|A singular deliverable component (not instantiated)|
|CBS|Configuration Breakdown Structure — hierarchy of usable components  the project is producing.  These are the types of items produced by a workflow.|
|RBS|Resource Breakdown Structure — hierarchy of people and teams|
|SBS|System Breakdown Structure.  Hierarchy of components needed to run the CBS objects to automate the EBS/ZBS objects.|
|S88 / ISA-88|International standard for batch process control|
|TBS|Time Breakdown Structure — calendar hierarchy and/or sprint schedule|
|Type|A reusable template defining attributes, workflow, and links for schedule objects|
|VBS|Value Breakdown Structure — hierarchy of business value for scope trade-off decisions|
|ZBS|Zone Breakdown Structure — hierarchy of physical/logical scope areas.  Maps to the S88 Equipment hierarchies when rooms/buildings/zones correspond to S88 Areas.  Can be used in conjunction with EBS when equipment is movable and operated in specific locations during manufacturing.|

\---

## 11\. References

* 4D-WBS Methodology: Adapted from field experience generating P6 schedules via matrix decomposition.
* DART Framework: Deliverables, Activities, Resources, Time — multi-dimensional scheduling model.
* ISA-88 / IEC 61512: Batch Process Control standard defining physical and procedural models.
* ISA-95 / IEC 62264: Enterprise-Control System Integration standard.
* IEC 61131-3: Programmable Controller programming languages and program organization.
* IEEE 15288: Systems and Software Engineering — System Lifecycle Processes.
* ANSI/EIA-748: Earned Value Management Systems standard.

