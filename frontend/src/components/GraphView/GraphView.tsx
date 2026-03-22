import { useCallback, useEffect, useMemo, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { useAppStore } from '../../store'
import { useObjects, useDocuments } from '../../hooks/useObjects'
import { useProjectReadinessSummary } from '../../hooks/useReadiness'
import { getRelationships } from '../../api/relationships'
import { applyDagreLayout } from './layout'
import ObjectNode from './ObjectNode'
import DocumentNode from './DocumentNode'

const NODE_TYPES = { objectNode: ObjectNode, documentNode: DocumentNode }

export default function GraphView() {
  const { selectedProjectId, setSelectedEntity, sliceFilters, hierarchyContext } = useAppStore()
  const hierarchyFilters = {
    area_id: hierarchyContext.areaId ?? undefined,
    unit_id: hierarchyContext.unitId ?? undefined,
  }
  const { data: objects = [] } = useObjects(selectedProjectId, sliceFilters, hierarchyFilters)
  const { data: documents = [] } = useDocuments(selectedProjectId)
  const { data: summary = [] } = useProjectReadinessSummary(selectedProjectId)
  const [relationships, setRelationships] = useState<{ source_entity_id: string; target_entity_id: string }[]>([])

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // Build a readiness lookup by entity id
  const readinessMap = useMemo(() => {
    const m: Record<string, { readiness: number; hasBlockers: boolean }> = {}
    summary.forEach((s) => {
      m[s.entity_id] = { readiness: s.overall_readiness, hasBlockers: s.blocker_count > 0 }
    })
    return m
  }, [summary])

  // Load relationships for all objects
  useEffect(() => {
    if (!objects.length) return
    Promise.all(objects.map((o) => getRelationships({ source_entity_id: o.id }))).then((results) => {
      setRelationships(results.flat())
    })
  }, [objects])

  // Build nodes and edges whenever data changes
  useEffect(() => {
    const rawNodes: Node[] = [
      ...objects.map((obj) => {
        const r = readinessMap[obj.id]
        return {
          id: obj.id,
          type: 'objectNode',
          position: { x: 0, y: 0 },
          data: {
            label: obj.name,
            objectType: obj.object_type,
            status: obj.status,
            readiness: r?.readiness ?? null,
            hasBlockers: r?.hasBlockers ?? false,
            onWhyBlocked: () => setSelectedEntity({ id: obj.id, type: 'object' }),
          },
        }
      }),
      ...documents.map((doc) => ({
        id: doc.id,
        type: 'documentNode',
        position: { x: 0, y: 0 },
        data: {
          label: doc.name,
          documentType: doc.document_type,
          status: doc.status,
        },
      })),
    ]

    const rawEdges: Edge[] = relationships.map((rel) => ({
      id: `${rel.source_entity_id}-${rel.target_entity_id}`,
      source: rel.source_entity_id,
      target: rel.target_entity_id,
      style: { stroke: '#94a3b8', strokeWidth: 1.5 },
      animated: false,
    }))

    const laid = applyDagreLayout(rawNodes, rawEdges)
    setNodes(laid)
    setEdges(rawEdges)
  }, [objects, documents, relationships, readinessMap, setNodes, setEdges, setSelectedEntity])

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const isDoc = documents.some((d) => d.id === node.id)
      setSelectedEntity({ id: node.id, type: isDoc ? 'document' : 'object' })
    },
    [documents, setSelectedEntity],
  )

  if (!selectedProjectId) return null

  if (!objects.length && !documents.length) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        No objects or documents in this project yet.
      </div>
    )
  }

  return (
    <div className="flex-1">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
      >
        <Background color="#e5e7eb" gap={20} />
        <Controls />
        <MiniMap nodeColor={(n) => {
          if (n.type === 'documentNode') return '#93c5fd'
          const r = readinessMap[n.id]
          if (!r) return '#d1d5db'
          if (r.hasBlockers || r.readiness < 0.5) return '#fca5a5'
          if (r.readiness < 0.9) return '#fcd34d'
          return '#86efac'
        }} />
      </ReactFlow>
    </div>
  )
}
