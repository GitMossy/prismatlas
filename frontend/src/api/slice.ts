import client from './client'
import type { SliceFilters, SliceResponse } from '../types'

export const querySlice = async (
  projectId: string,
  filters: Partial<SliceFilters>,
): Promise<SliceResponse> => {
  const body = {
    zone: filters.zone ?? null,
    stage: filters.stage ?? null,
    planned_after: filters.planned_after ?? null,
    planned_before: filters.planned_before ?? null,
    owner: filters.owner ?? null,
    object_type: filters.object_type ?? null,
  }
  const { data } = await client.post(`/projects/${projectId}/slice`, body)
  return data
}
