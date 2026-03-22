// ---- Projects ----

export interface Project {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface Area {
  id: string
  project_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface Unit {
  id: string
  area_id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

// ---- Objects ----

export interface HierarchyContext {
  areaId: string | null
  unitId: string | null
}

export interface ProjectObject {
  id: string
  project_id: string
  area_id: string | null
  unit_id: string | null
  parent_object_id: string | null
  class_definition_id: string | null
  name: string
  object_type: string
  status: string
  description: string | null
  zone: string | null
  planned_start: string | null
  planned_end: string | null
  owner: string | null
  created_at: string
  updated_at: string
}

// ---- Documents ----

export interface Document {
  id: string
  project_id: string
  name: string
  document_type: string
  status: string
  description: string | null
  external_ref: string | null
  created_at: string
  updated_at: string
}

// ---- Workflow ----

export interface TaskInstance {
  id: string
  stage_instance_id: string
  task_key: string
  task_name: string
  task_order: number
  is_mandatory: boolean
  status: string
  completed_at: string | null
  completed_by: string | null
  notes: string | null
  // Scheduling fields
  duration_days: number | null
  effort_hours: number | null
  assigned_resource_id: string | null
  early_start: number | null
  early_finish: number | null
  late_start: number | null
  late_finish: number | null
  total_float: number | null
  is_critical: boolean
}

export interface StageInstance {
  id: string
  workflow_instance_id: string
  stage_key: string
  stage_name: string
  stage_order: number
  status: string
  started_at: string | null
  completed_at: string | null
  task_instances: TaskInstance[]
}

export interface WorkflowInstance {
  id: string
  entity_type: string
  entity_id: string
  template_version_id: string
  status: string
  created_at: string
  updated_at: string
  stage_instances: StageInstance[]
}

// ---- Readiness ----

export interface Blocker {
  type: 'document' | 'dependency' | 'task' | 'stage_gate' | 'class'
  entity_id: string
  entity_name: string
  reason: string
  severity: 'blocking' | 'warning'
}

export interface ReadinessEvaluation {
  id: string
  entity_type: string
  entity_id: string
  technical_readiness: number
  document_readiness: number
  stage_readiness: number
  overall_readiness: number
  ready_for_fat: boolean
  ready_for_sat: boolean
  blockers: Blocker[]
  next_action: string | null
  evaluated_at: string
}

export interface ProjectReadinessSummaryItem {
  entity_id: string
  entity_name: string
  entity_type: string
  object_type: string | null
  overall_readiness: number
  ready_for_fat: boolean
  ready_for_sat: boolean
  blocker_count: number
}

export interface AreaReadinessSummary {
  area_id: string
  area_name: string
  object_count: number
  avg_readiness: number
  fat_ready_count: number
  sat_ready_count: number
  blocker_count: number
}

// ---- Relationships ----

export interface Relationship {
  id: string
  source_entity_type: string
  source_entity_id: string
  target_entity_type: string
  target_entity_id: string
  relationship_type: string
  is_mandatory: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

// ---- Workflow Templates (Designer) ----

export interface CriterionDef {
  type: string           // "all_tasks_complete" | "stage_complete" | "document_status" | "manual_approval"
  stage_key?: string
  document_type?: string
  required_status?: string
}

export interface TaskDef {
  key: string
  name: string
  order: number
  is_mandatory: boolean
  duration_days?: number
  effort_hours?: number
}

export interface StageDef {
  key: string
  name: string
  order: number
  is_mandatory: boolean
  entry_criteria: CriterionDef[]
  exit_criteria: CriterionDef[]
  tasks: TaskDef[]
}

export interface TemplateDef {
  stages: StageDef[]
}

export interface WorkflowTemplate {
  id: string
  name: string
  applies_to_type: string
  description: string | null
  complexity: number
  custom_attributes: unknown[] | null
  created_at: string
  updated_at: string
}

export interface WorkflowTemplateVersion {
  id: string
  template_id: string
  version_number: number
  definition: TemplateDef
  is_active: boolean
  created_at: string
}

// ---- Slice ----

export interface SliceFilters {
  zone: string | null
  stage: string | null
  planned_after: string | null
  planned_before: string | null
  owner: string | null
  object_type: string | null
}

export interface SliceResultItem {
  entity_id: string
  entity_name: string
  zone: string | null
  owner: string | null
  object_type: string | null
  planned_start: string | null
  planned_end: string | null
  current_stage: string | null
  overall_readiness: number
  ready_for_fat: boolean
  ready_for_sat: boolean
  blocker_count: number
  top_blocker: string | null
}

export interface SliceResponse {
  query: Record<string, unknown>
  total: number
  results: SliceResultItem[]
  avg_readiness: number
  fat_ready_count: number
  sat_ready_count: number
  total_blockers: number
  common_blocker_types: string[]
}

// ---- Resources ----

export interface Resource {
  id: string
  project_id: string
  name: string
  role: string | null
  group: string | null
  email: string | null
  capacity_hours_per_day: number
  notes: string | null
  created_at: string
  updated_at: string
}

// ---- Class Definitions (PBS / Instance Set) ----

export interface ClassDefinition {
  id: string
  project_id: string
  area_id: string | null
  workflow_template_id: string | null
  name: string
  object_type: string
  description: string | null
  instance_count: number
  complexity: number
  effort_scaling_mode: string
  custom_attributes: unknown[] | null
  created_at: string
  updated_at: string
}

// ---- Schedule / CPM ----

export interface TaskScheduleRow {
  task_id: string
  task_key: string
  task_name: string
  stage_key: string
  stage_name: string
  duration_days: number | null
  effort_hours: number | null
  assigned_resource_id: string | null
  early_start: number | null
  early_finish: number | null
  late_start: number | null
  late_finish: number | null
  total_float: number | null
  is_critical: boolean
}

export interface ScheduleResponse {
  workflow_instance_id: string
  project_duration_days: number
  critical_path_task_ids: string[]
  tasks: TaskScheduleRow[]
}

// ---- Matrix ----

export interface MatrixCell {
  row: string
  col: string
  value: number | string
  color: string
}

export interface MatrixData {
  row_labels: string[]
  col_labels: string[]
  cells: MatrixCell[]
}

export interface SavedView {
  id: string
  project_id: string
  user_id: string | null
  name: string
  config: Record<string, unknown>
}

// ---- Zone Diagrams ----

export interface ZoneDiagramPin {
  id: string
  zone_diagram_id: string
  object_id: string
  x_pct: number
  y_pct: number
}

export interface ZoneDiagram {
  id: string
  area_id: string
  name: string
  image_url: string
  image_width: number
  image_height: number
  pins: ZoneDiagramPin[]
}

// ---- Hierarchy ----

export interface HierarchyNode {
  id: string
  project_id: string
  dimension: string
  name: string
  description: string | null
  parent_id: string | null
  position: number
  workflow_template_id: string | null
  workflow_template_name: string | null
  depends_on_node_id: string | null
  depends_on_node_name: string | null
  dependency_condition: Record<string, string> | null
  children: HierarchyNode[]
}

// ---- UI state ----

export type ViewMode = 'dashboard' | 'graph' | 'list' | 'cube' | 'gantt' | 'matrix' | 'library' | 'settings'

export type EntityType = 'object' | 'document'

export interface SelectedEntity {
  id: string
  type: EntityType
}
