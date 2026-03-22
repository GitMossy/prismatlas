import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { hierarchyApi, type HierarchyMember } from '../api/hierarchy'

export type { HierarchyMember }

export const DIMENSIONS = ['ZBS', 'OBS', 'TBS', 'VBS', 'RBS'] as const
export type Dimension = typeof DIMENSIONS[number]

export const useHierarchyNodes = (projectId: string | null, dimension?: string) =>
  useQuery({
    queryKey: ['hierarchy-nodes', projectId, dimension],
    queryFn: () => hierarchyApi.listNodes(projectId!, dimension),
    enabled: !!projectId,
  })

export const useCreateHierarchyNode = (projectId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      dimension: string
      name: string
      description?: string
      parent_id?: string | null
      position?: number
    }) => hierarchyApi.createNode({ project_id: projectId, ...body }),
    onSuccess: (_data, variables) =>
      qc.invalidateQueries({ queryKey: ['hierarchy-nodes', projectId, variables.dimension] }),
  })
}

export const useDeleteHierarchyNode = (projectId: string, dimension: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (nodeId: string) => hierarchyApi.deleteNode(nodeId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['hierarchy-nodes', projectId, dimension] }),
  })
}

export const useHierarchyNodeMembers = (nodeId: string | null) =>
  useQuery({
    queryKey: ['hierarchy-node-members', nodeId],
    queryFn: () => hierarchyApi.listMembers(nodeId!),
    enabled: !!nodeId,
  })

export const useAddHierarchyMember = (nodeId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { entity_type: string; entity_id: string }) =>
      hierarchyApi.addMember(nodeId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hierarchy-node-members', nodeId] }),
  })
}

export const useMoveHierarchyNode = (projectId: string, dimension: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ nodeId, parent_id, position }: { nodeId: string; parent_id: string | null; position: number }) =>
      hierarchyApi.moveNode(nodeId, { parent_id, position }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['hierarchy-nodes', projectId, dimension] }),
  })
}
