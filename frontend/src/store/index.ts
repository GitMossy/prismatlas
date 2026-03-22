import { create } from 'zustand'
import type { HierarchyContext, SelectedEntity, SliceFilters, ViewMode } from '../types'

const DEFAULT_SLICE_FILTERS: SliceFilters = {
  zone: null,
  stage: null,
  planned_after: null,
  planned_before: null,
  owner: null,
  object_type: null,
}

// Hierarchy dimensions available as cube/pivot axes (V3 FR-4.1 — CBS, ABS, SBS added)
export type HierarchyDimension = 'ZBS' | 'EBS' | 'OBS' | 'TBS' | 'VBS' | 'RBS' | 'CBS' | 'ABS' | 'SBS'

export type CubeDimension = 'zone' | 'stage' | 'owner' | 'object_type' | HierarchyDimension

export interface CubeAxes {
  x: CubeDimension
  y: CubeDimension
  z: CubeDimension
}

export type SortDir = 'asc' | 'desc'

export interface CubeAxisSort {
  x: SortDir
  y: SortDir
  z: SortDir
}

const DEFAULT_CUBE_AXES: CubeAxes     = { x: 'object_type', y: 'stage', z: 'zone' }
const DEFAULT_CUBE_SORT: CubeAxisSort = { x: 'asc', y: 'asc', z: 'asc' }

export interface MatrixConfig {
  view: string
  rows?: string
  cols?: string
  metric?: string
}

interface AppState {
  selectedProjectId: string | null
  selectedEntity: SelectedEntity | null
  viewMode: ViewMode
  sliceFilters: SliceFilters
  cubeAxes: CubeAxes
  cubeAxisSort: CubeAxisSort
  hierarchyContext: HierarchyContext
  hierarchyNodeId: string | null
  matrixConfig: MatrixConfig
  setSelectedProject: (id: string | null) => void
  setSelectedEntity: (entity: SelectedEntity | null) => void
  setViewMode: (mode: ViewMode) => void
  setSliceFilters: (filters: Partial<SliceFilters>) => void
  resetSliceFilters: () => void
  setCubeAxes: (axes: Partial<CubeAxes>) => void
  setCubeAxisSort: (sort: Partial<CubeAxisSort>) => void
  setHierarchyArea: (areaId: string | null) => void
  setHierarchyUnit: (areaId: string, unitId: string) => void
  clearHierarchyContext: () => void
  setHierarchyNode: (nodeId: string | null) => void
  setMatrixConfig: (config: Partial<MatrixConfig>) => void
}

const DEFAULT_MATRIX_CONFIG: MatrixConfig = { view: 'task-status' }

export const useAppStore = create<AppState>((set) => ({
  selectedProjectId: null,
  selectedEntity: null,
  viewMode: 'dashboard',
  sliceFilters: { ...DEFAULT_SLICE_FILTERS },
  cubeAxes: { ...DEFAULT_CUBE_AXES },
  cubeAxisSort: { ...DEFAULT_CUBE_SORT },
  hierarchyContext: { areaId: null, unitId: null },
  hierarchyNodeId: null,
  matrixConfig: { ...DEFAULT_MATRIX_CONFIG },
  setSelectedProject: (id) => set({ selectedProjectId: id, selectedEntity: null, hierarchyContext: { areaId: null, unitId: null }, hierarchyNodeId: null }),
  setSelectedEntity: (entity) => set({ selectedEntity: entity }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setSliceFilters: (filters) =>
    set((state) => ({ sliceFilters: { ...state.sliceFilters, ...filters } })),
  resetSliceFilters: () => set({ sliceFilters: { ...DEFAULT_SLICE_FILTERS } }),
  setCubeAxes: (incoming) =>
    set((state) => {
      const prev = state.cubeAxes
      const next = { ...prev, ...incoming }
      const axes = ['x', 'y', 'z'] as const
      for (const changed of axes) {
        if (!(changed in incoming)) continue
        const newDim = next[changed]
        for (const other of axes) {
          if (other !== changed && next[other] === newDim) {
            next[other] = prev[changed]
          }
        }
      }
      return { cubeAxes: next }
    }),
  setCubeAxisSort: (sort) =>
    set((state) => ({ cubeAxisSort: { ...state.cubeAxisSort, ...sort } })),
  setHierarchyArea: (areaId) => set({ hierarchyContext: { areaId, unitId: null } }),
  setHierarchyUnit: (areaId, unitId) => set({ hierarchyContext: { areaId, unitId } }),
  clearHierarchyContext: () => set({ hierarchyContext: { areaId: null, unitId: null } }),
  setHierarchyNode: (nodeId) => set({ hierarchyNodeId: nodeId }),
  setMatrixConfig: (config) =>
    set((state) => ({ matrixConfig: { ...state.matrixConfig, ...config } })),
}))
