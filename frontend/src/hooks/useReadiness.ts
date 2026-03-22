import { useQuery } from '@tanstack/react-query'
import { getReadiness, getProjectReadinessSummary, getProjectFatReadiness, getAreaSummary } from '../api/readiness'

export const useReadiness = (entityId: string | null) =>
  useQuery({
    queryKey: ['readiness', entityId],
    queryFn: () => getReadiness(entityId!),
    enabled: !!entityId,
    retry: false, // No evaluation yet is a normal state — don't spam the API
  })

export const useProjectReadinessSummary = (projectId: string | null) =>
  useQuery({
    queryKey: ['readiness-summary', projectId],
    queryFn: () => getProjectReadinessSummary(projectId!),
    enabled: !!projectId,
  })

export const useProjectFatReadiness = (projectId: string | null) =>
  useQuery({
    queryKey: ['fat-readiness', projectId],
    queryFn: () => getProjectFatReadiness(projectId!),
    enabled: !!projectId,
  })

export const useAreaSummary = (projectId: string | null) =>
  useQuery({
    queryKey: ['area-summary', projectId],
    queryFn: () => getAreaSummary(projectId!),
    enabled: !!projectId,
  })
