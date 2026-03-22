import client from './client'
import type { MatrixData, SavedView } from '../types'

// V3: RACI row type (FR-4.6.1h)
export interface RACIRow {
  resource_name: string
  step_key: string
  raci_role: 'R' | 'A' | 'C' | 'I'
}

// V3: Resource assignment cell type (FR-4.6.1d)
export interface AllocationCell {
  resource_name: string
  cbs_item: string
  allocation_pct: number
}

export const matrixApi = {
  taskStatus: (projectId: string): Promise<MatrixData> =>
    client.get(`/projects/${projectId}/matrix/task-status`).then((r) => r.data),

  resourceLoading: (
    projectId: string,
    params: { start_day?: number; end_day?: number; bucket?: string } = {}
  ): Promise<MatrixData> =>
    client
      .get(`/projects/${projectId}/matrix/resource-loading`, { params })
      .then((r) => r.data),

  areaHeatmap: (projectId: string, metric: string): Promise<MatrixData> =>
    client
      .get(`/projects/${projectId}/matrix/area-heatmap`, { params: { metric } })
      .then((r) => r.data),

  custom: (
    projectId: string,
    params: { rows: string; cols: string; metric: string }
  ): Promise<MatrixData> =>
    client
      .get(`/projects/${projectId}/matrix/custom`, { params })
      .then((r) => r.data),

  // V3 FR-4.6.1h — RACI Chart (RBS × ABS)
  raci: (projectId: string): Promise<RACIRow[]> =>
    client.get(`/projects/${projectId}/matrix/raci`).then((r) => r.data),

  // V3 FR-4.6.1d — Resource Assignment (RBS × CBS)
  resourceAssignment: (projectId: string): Promise<AllocationCell[]> =>
    client.get(`/projects/${projectId}/matrix/resource-assignment`).then((r) => r.data),

  listSavedViews: (projectId: string): Promise<SavedView[]> =>
    client.get(`/projects/${projectId}/saved-views`).then((r) => r.data),

  createSavedView: (
    projectId: string,
    body: { name: string; config: Record<string, unknown> }
  ): Promise<SavedView> =>
    client.post(`/projects/${projectId}/saved-views`, body).then((r) => r.data),
}
