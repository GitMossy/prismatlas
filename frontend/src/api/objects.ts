import client from './client'
import type { ProjectObject } from '../types'

export const getObjects = async (params: {
  project_id?: string
  area_id?: string
  unit_id?: string
  type?: string
  status?: string
  zone?: string
  owner?: string
  stage?: string
  planned_after?: string
  planned_before?: string
}): Promise<ProjectObject[]> => {
  const { data } = await client.get('/objects', { params })
  return data
}

export const getObject = async (id: string): Promise<ProjectObject> => {
  const { data } = await client.get(`/objects/${id}`)
  return data
}

export interface ObjectCreatePayload {
  project_id: string
  area_id?: string | null
  unit_id?: string | null
  parent_object_id?: string | null
  name: string
  object_type: string
  status?: string
  description?: string | null
  zone?: string | null
  planned_start?: string | null
  planned_end?: string | null
  owner?: string | null
}

export type ObjectUpdatePayload = Partial<Omit<ObjectCreatePayload, 'project_id'>>

export const createObject = async (payload: ObjectCreatePayload): Promise<ProjectObject> => {
  const { data } = await client.post('/objects', payload)
  return data
}

export const updateObject = async (id: string, payload: ObjectUpdatePayload): Promise<ProjectObject> => {
  const { data } = await client.put(`/objects/${id}`, payload)
  return data
}

export const deleteObject = async (id: string): Promise<void> => {
  await client.delete(`/objects/${id}`)
}
