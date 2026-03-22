import client from './client'
import type { Area, Project, Unit } from '../types'

export const getProjects = async (): Promise<Project[]> => {
  const { data } = await client.get('/projects')
  return data
}

export const getProject = async (id: string): Promise<Project> => {
  const { data } = await client.get(`/projects/${id}`)
  return data
}

export const createProject = async (payload: { name: string; description?: string }): Promise<Project> => {
  const { data } = await client.post('/projects', payload)
  return data
}

export const updateProject = async (id: string, payload: { name?: string; description?: string }): Promise<Project> => {
  const { data } = await client.put(`/projects/${id}`, payload)
  return data
}

export const deleteProject = async (id: string): Promise<void> => {
  await client.delete(`/projects/${id}`)
}

export const getAreas = async (projectId: string): Promise<Area[]> => {
  const { data } = await client.get('/areas', { params: { project_id: projectId } })
  return data
}

export const createArea = async (payload: { project_id: string; name: string; description?: string }): Promise<Area> => {
  const { data } = await client.post('/areas', payload)
  return data
}

export const updateArea = async (id: string, payload: { name?: string; description?: string }): Promise<Area> => {
  const { data } = await client.put(`/areas/${id}`, payload)
  return data
}

export const deleteArea = async (id: string): Promise<void> => {
  await client.delete(`/areas/${id}`)
}

export const getUnits = async (areaId: string): Promise<Unit[]> => {
  const { data } = await client.get('/units', { params: { area_id: areaId } })
  return data
}

export const createUnit = async (payload: { area_id: string; name: string; description?: string }): Promise<Unit> => {
  const { data } = await client.post('/units', payload)
  return data
}

export const updateUnit = async (id: string, payload: { name?: string; description?: string }): Promise<Unit> => {
  const { data } = await client.put(`/units/${id}`, payload)
  return data
}

export const deleteUnit = async (id: string): Promise<void> => {
  await client.delete(`/units/${id}`)
}
