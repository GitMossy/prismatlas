import client from './client'
import type { Relationship } from '../types'

export const getRelationships = async (params: {
  source_entity_id?: string
  target_entity_id?: string
}): Promise<Relationship[]> => {
  const { data } = await client.get('/relationships', { params })
  return data
}
