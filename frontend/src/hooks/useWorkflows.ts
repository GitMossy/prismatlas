import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listTemplates,
  getTemplate,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  listTemplateVersions,
  createTemplateVersion,
  deleteTemplateVersion,
  activateTemplateVersion,
} from '../api/workflows'
import type { TemplateDef } from '../types'

export const useTemplates = () =>
  useQuery({ queryKey: ['workflow-templates'], queryFn: listTemplates })

export const useTemplate = (id: string | null) =>
  useQuery({
    queryKey: ['workflow-templates', id],
    queryFn: () => getTemplate(id!),
    enabled: !!id,
  })

export const useTemplateVersions = (templateId: string | null) =>
  useQuery({
    queryKey: ['workflow-template-versions', templateId],
    queryFn: () => listTemplateVersions(templateId!),
    enabled: !!templateId,
  })

export const useCreateTemplate = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createTemplate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflow-templates'] }),
  })
}

export const useCreateTemplateVersion = (templateId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (definition: TemplateDef) => createTemplateVersion(templateId, definition),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflow-template-versions', templateId] }),
  })
}

export const useUpdateTemplate = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: string; name?: string; applies_to_type?: string; description?: string }) =>
      updateTemplate(id, payload),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['workflow-templates'] })
      qc.invalidateQueries({ queryKey: ['workflow-templates', id] })
    },
  })
}

export const useDeleteTemplate = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteTemplate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflow-templates'] }),
  })
}

export const useDeleteTemplateVersion = (templateId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (versionNumber: number) => deleteTemplateVersion(templateId, versionNumber),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflow-template-versions', templateId] }),
  })
}

export const useActivateTemplateVersion = (templateId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (versionNumber: number) => activateTemplateVersion(templateId, versionNumber),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflow-template-versions', templateId] }),
  })
}
