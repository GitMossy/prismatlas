import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { matrixApi } from '../api/matrix'
import type { RACIRow, AllocationCell } from '../api/matrix'

export const useTaskStatusMatrix = (projectId: string | null) =>
  useQuery({
    queryKey: ['matrix', 'task-status', projectId],
    queryFn: () => matrixApi.taskStatus(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  })

export const useResourceLoading = (
  projectId: string | null,
  params: { start_day?: number; end_day?: number; bucket?: string } = {}
) =>
  useQuery({
    queryKey: ['matrix', 'resource-loading', projectId, params],
    queryFn: () => matrixApi.resourceLoading(projectId!, params),
    enabled: !!projectId,
    staleTime: 30_000,
  })

export const useAreaHeatmap = (projectId: string | null, metric: string) =>
  useQuery({
    queryKey: ['matrix', 'area-heatmap', projectId, metric],
    queryFn: () => matrixApi.areaHeatmap(projectId!, metric),
    enabled: !!projectId,
    staleTime: 30_000,
  })

export const useCustomMatrix = (
  projectId: string | null,
  params: { rows: string; cols: string; metric: string }
) =>
  useQuery({
    queryKey: ['matrix', 'custom', projectId, params],
    queryFn: () => matrixApi.custom(projectId!, params),
    enabled: !!projectId,
    staleTime: 30_000,
  })

export const useSavedViews = (projectId: string | null) =>
  useQuery({
    queryKey: ['saved-views', projectId],
    queryFn: () => matrixApi.listSavedViews(projectId!),
    enabled: !!projectId,
  })

export const useCreateSavedView = (projectId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; config: Record<string, unknown> }) =>
      matrixApi.createSavedView(projectId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['saved-views', projectId] }),
  })
}

// V3 FR-4.6.1h — RACI chart hook
export const useRACIMatrix = (projectId: string | null) =>
  useQuery<RACIRow[]>({
    queryKey: ['matrix', 'raci', projectId],
    queryFn: () => matrixApi.raci(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  })

// V3 FR-4.6.1d — Resource assignment hook
export const useResourceAssignment = (projectId: string | null) =>
  useQuery<AllocationCell[]>({
    queryKey: ['matrix', 'resource-assignment', projectId],
    queryFn: () => matrixApi.resourceAssignment(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  })
