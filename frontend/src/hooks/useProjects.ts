import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getProjects, getProject, createProject, updateProject, deleteProject,
  getAreas, createArea, updateArea, deleteArea,
  getUnits, createUnit, updateUnit, deleteUnit,
} from '../api/projects'

export const useProjects = () =>
  useQuery({ queryKey: ['projects'], queryFn: getProjects })

export const useProject = (id: string | null) =>
  useQuery({ queryKey: ['projects', id], queryFn: () => getProject(id!), enabled: !!id })

export const useCreateProject = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createProject,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export const useUpdateProject = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: string; name?: string; description?: string }) =>
      updateProject(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export const useDeleteProject = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteProject,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export const useAreas = (projectId: string | null) =>
  useQuery({ queryKey: ['areas', projectId], queryFn: () => getAreas(projectId!), enabled: !!projectId })

export const useCreateArea = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createArea,
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ['areas', vars.project_id] }),
  })
}

export const useUpdateArea = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: string; project_id: string; name?: string; description?: string }) =>
      updateArea(id, payload),
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ['areas', vars.project_id] }),
  })
}

export const useDeleteArea = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string; project_id: string }) => deleteArea(id),
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ['areas', vars.project_id] }),
  })
}

export const useUnits = (areaId: string | null) =>
  useQuery({ queryKey: ['units', areaId], queryFn: () => getUnits(areaId!), enabled: !!areaId })

export const useCreateUnit = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createUnit,
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ['units', vars.area_id] }),
  })
}

export const useUpdateUnit = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: string; area_id: string; name?: string; description?: string }) =>
      updateUnit(id, payload),
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ['units', vars.area_id] }),
  })
}

export const useDeleteUnit = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string; area_id: string }) => deleteUnit(id),
    onSuccess: (_data, vars) => qc.invalidateQueries({ queryKey: ['units', vars.area_id] }),
  })
}
