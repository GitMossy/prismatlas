import client from './client'
import type { WorkflowTemplate, WorkflowTemplateVersion, TemplateDef } from '../types'

export const listTemplates = async (): Promise<WorkflowTemplate[]> => {
  const { data } = await client.get('/workflow-templates')
  return data
}

export const getTemplate = async (id: string): Promise<WorkflowTemplate> => {
  const { data } = await client.get(`/workflow-templates/${id}`)
  return data
}

export const createTemplate = async (payload: {
  name: string
  applies_to_type: string
  description?: string
}): Promise<WorkflowTemplate> => {
  const { data } = await client.post('/workflow-templates', payload)
  return data
}

export const listTemplateVersions = async (templateId: string): Promise<WorkflowTemplateVersion[]> => {
  const { data } = await client.get(`/workflow-templates/${templateId}/versions`)
  return data
}

export const getTemplateVersion = async (
  templateId: string,
  versionNumber: number,
): Promise<WorkflowTemplateVersion> => {
  const { data } = await client.get(`/workflow-templates/${templateId}/versions/${versionNumber}`)
  return data
}

export const createTemplateVersion = async (
  templateId: string,
  definition: TemplateDef,
): Promise<WorkflowTemplateVersion> => {
  const { data } = await client.post(`/workflow-templates/${templateId}/versions`, { definition })
  return data
}

export const updateTemplate = async (
  id: string,
  payload: { name?: string; applies_to_type?: string; description?: string },
): Promise<WorkflowTemplate> => {
  const { data } = await client.put(`/workflow-templates/${id}`, payload)
  return data
}

export const deleteTemplate = async (id: string): Promise<void> => {
  await client.delete(`/workflow-templates/${id}`)
}

export const deleteTemplateVersion = async (templateId: string, versionNumber: number): Promise<void> => {
  await client.delete(`/workflow-templates/${templateId}/versions/${versionNumber}`)
}

export const activateTemplateVersion = async (
  templateId: string,
  versionNumber: number,
): Promise<WorkflowTemplateVersion> => {
  const { data } = await client.patch(`/workflow-templates/${templateId}/versions/${versionNumber}/activate`)
  return data
}
