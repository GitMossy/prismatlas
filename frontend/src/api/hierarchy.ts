import client from './client'
import type { HierarchyNode } from '../types'

export const hierarchyApi = {
  listNodes: (projectId: string, dimension?: string): Promise<HierarchyNode[]> =>
    client
      .get('/hierarchy-nodes', { params: { project_id: projectId, ...(dimension ? { dimension } : {}) } })
      .then((r) => r.data),

  createNode: (body: {
    project_id: string
    dimension: string
    name: string
    description?: string
    parent_id?: string | null
    position?: number
  }): Promise<HierarchyNode> =>
    client.post('/hierarchy-nodes', body).then((r) => r.data),

  getNode: (nodeId: string): Promise<HierarchyNode> =>
    client.get(`/hierarchy-nodes/${nodeId}`).then((r) => r.data),

  updateNode: (
    nodeId: string,
    body: {
      name?: string
      description?: string
      position?: number
      workflow_template_id?: string | null
      depends_on_node_id?: string | null
      dependency_condition?: Record<string, string> | null
    }
  ): Promise<HierarchyNode> =>
    client.put(`/hierarchy-nodes/${nodeId}`, body).then((r) => r.data),

  deleteNode: (nodeId: string): Promise<void> =>
    client.delete(`/hierarchy-nodes/${nodeId}`).then(() => undefined),

  moveNode: (
    nodeId: string,
    body: { parent_id: string | null; position: number }
  ): Promise<HierarchyNode> =>
    client.patch(`/hierarchy-nodes/${nodeId}/move`, body).then((r) => r.data),

  listMembers: (nodeId: string): Promise<HierarchyMember[]> =>
    client.get(`/hierarchy-nodes/${nodeId}/members`).then((r) => r.data),

  addMember: (nodeId: string, body: { entity_type: string; entity_id: string }): Promise<HierarchyMember> =>
    client.post(`/hierarchy-nodes/${nodeId}/members`, body).then((r) => r.data),

  removeMember: (nodeId: string, entityId: string): Promise<void> =>
    client.delete(`/hierarchy-nodes/${nodeId}/members/${entityId}`).then(() => undefined),
}

export interface HierarchyMember {
  entity_type: string
  entity_id: string
  name: string
  object_type: string | null
}

export interface NodeMembership {
  node_id: string
  entity_id: string
  entity_type: string
  name: string
  object_type: string | null
  status: string | null
}

// All memberships across every node in a dimension — single call for dashboard rollup
export const getProjectHierarchyMemberships = (
  projectId: string,
  dimension = 'ZBS',
): Promise<NodeMembership[]> =>
  client
    .get(`/projects/${projectId}/hierarchy/memberships`, { params: { dimension } })
    .then((r) => r.data)
