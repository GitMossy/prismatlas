import { useQuery } from '@tanstack/react-query'
import { getObjects } from '../api/objects'
import { getDocuments } from '../api/documents'
import { getRelationships } from '../api/relationships'
import type { SliceFilters } from '../types'

export const useObjects = (
  projectId: string | null,
  filters?: Partial<SliceFilters>,
  hierarchyFilters?: { area_id?: string; unit_id?: string },
) =>
  useQuery({
    queryKey: ['objects', projectId, filters, hierarchyFilters],
    queryFn: () =>
      getObjects({
        project_id: projectId!,
        zone: filters?.zone ?? undefined,
        owner: filters?.owner ?? undefined,
        stage: filters?.stage ?? undefined,
        planned_after: filters?.planned_after ?? undefined,
        planned_before: filters?.planned_before ?? undefined,
        type: filters?.object_type ?? undefined,
        area_id: hierarchyFilters?.area_id,
        unit_id: hierarchyFilters?.unit_id,
      }),
    enabled: !!projectId,
  })

export const useDocuments = (projectId: string | null) =>
  useQuery({
    queryKey: ['documents', projectId],
    queryFn: () => getDocuments({ project_id: projectId! }),
    enabled: !!projectId,
  })

export const useRelationships = (sourceEntityId?: string) =>
  useQuery({
    queryKey: ['relationships', sourceEntityId],
    queryFn: () => getRelationships({ source_entity_id: sourceEntityId }),
    enabled: !!sourceEntityId,
  })
