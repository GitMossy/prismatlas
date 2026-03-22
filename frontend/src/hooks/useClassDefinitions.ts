import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { classDefinitionsApi, type ClassDefinitionCreate, type ClassDefinitionUpdate } from '../api/classDefinitions'

export function useClassDefinitions(projectId: string | null, objectType?: string) {
  return useQuery({
    queryKey: ['class-definitions', projectId, objectType],
    queryFn: () => classDefinitionsApi.list(projectId!, objectType),
    enabled: !!projectId,
  })
}

export function useCreateClassDefinition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: ClassDefinitionCreate) => classDefinitionsApi.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['class-definitions'] }),
  })
}

export function useUpdateClassDefinition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: string } & ClassDefinitionUpdate) =>
      classDefinitionsApi.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['class-definitions'] }),
  })
}

export function useDeleteClassDefinition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => classDefinitionsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['class-definitions'] }),
  })
}
