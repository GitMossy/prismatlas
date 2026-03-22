import { useQuery } from '@tanstack/react-query'
import { querySlice } from '../api/slice'
import type { SliceFilters } from '../types'

export const useSliceQuery = (projectId: string | null, filters: Partial<SliceFilters>) =>
  useQuery({
    queryKey: ['slice', projectId, filters],
    queryFn: () => querySlice(projectId!, filters),
    enabled: !!projectId,
  })
