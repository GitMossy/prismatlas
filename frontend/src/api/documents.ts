import client from './client'
import type { Document } from '../types'

export const getDocuments = async (params: {
  project_id?: string
  type?: string
  status?: string
}): Promise<Document[]> => {
  const { data } = await client.get('/documents', { params })
  return data
}

export const getDocument = async (id: string): Promise<Document> => {
  const { data } = await client.get(`/documents/${id}`)
  return data
}
