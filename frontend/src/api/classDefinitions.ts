import client from './client'
import type { ClassDefinition } from '../types'

export interface ClassDefinitionCreate {
  project_id: string
  area_id?: string | null
  workflow_template_id?: string | null
  name: string
  object_type: string
  description?: string | null
  instance_count?: number
  complexity?: number
}

export interface ClassDefinitionUpdate {
  name?: string
  area_id?: string | null
  workflow_template_id?: string | null
  description?: string | null
  instance_count?: number
  complexity?: number
}

export const classDefinitionsApi = {
  list: (projectId: string, objectType?: string): Promise<ClassDefinition[]> =>
    client.get('/class-definitions', {
      params: { project_id: projectId, ...(objectType ? { object_type: objectType } : {}) },
    }).then((r) => r.data),

  get: (id: string): Promise<ClassDefinition> =>
    client.get(`/class-definitions/${id}`).then((r) => r.data),

  create: (payload: ClassDefinitionCreate): Promise<ClassDefinition> =>
    client.post('/class-definitions', payload).then((r) => r.data),

  update: (id: string, payload: ClassDefinitionUpdate): Promise<ClassDefinition> =>
    client.put(`/class-definitions/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    client.delete(`/class-definitions/${id}`).then(() => undefined),
}
