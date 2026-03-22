import client from './client'
import type { ReadinessEvaluation, ProjectReadinessSummaryItem, AreaReadinessSummary } from '../types'

export const getReadiness = async (entityId: string): Promise<ReadinessEvaluation> => {
  const { data } = await client.get(`/entities/${entityId}/readiness`)
  return data
}

export const evaluateReadiness = async (entityId: string, entityType: string): Promise<ReadinessEvaluation> => {
  const { data } = await client.post(`/entities/${entityId}/readiness/evaluate`, null, {
    params: { entity_type: entityType },
  })
  return data
}

export const getProjectReadinessSummary = async (projectId: string): Promise<ProjectReadinessSummaryItem[]> => {
  const { data } = await client.get(`/projects/${projectId}/readiness-summary`)
  return data
}

export const getProjectFatReadiness = async (projectId: string): Promise<ProjectReadinessSummaryItem[]> => {
  const { data } = await client.get(`/projects/${projectId}/fat-readiness`)
  return data
}

export const getAreaSummary = async (projectId: string): Promise<AreaReadinessSummary[]> => {
  const { data } = await client.get(`/projects/${projectId}/area-summary`)
  return data
}

export const getBlockers = async (entityId: string) => {
  const { data } = await client.get(`/entities/${entityId}/blockers`)
  return data
}

export interface DependencyRuleDetail {
  id: string
  name: string
  target_entity_id: string
  target_entity_name: string
  target_entity_status: string | null
  condition: Record<string, string>
  is_mandatory: boolean
  link_type: string
  lag_days: number
  satisfied: boolean
  reason: string | null
}

export const getDependencyRules = async (entityId: string): Promise<DependencyRuleDetail[]> => {
  const { data } = await client.get(`/entities/${entityId}/dependency-rules`, {
    params: { entity_type: 'object' },
  })
  return data
}
