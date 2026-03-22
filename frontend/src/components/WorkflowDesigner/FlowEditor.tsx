/**
 * FlowEditor — Visual flowchart view for Workflow Designer — FR-4.3.1
 *
 * Converts TemplateDef.stages to React Flow nodes/edges.
 * - entry_criteria with type "stage_complete" become directed edges
 * - User can drag stages to reposition
 * - Connecting B → A adds {type:"stage_complete", stage_key:"B"} to A's entry_criteria
 * - Clicking a node selects the stage for editing
 * - Syncs back to parent TemplateDef state on every change
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
  type Node,
  type NodeMouseHandler,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { TemplateDef, StageDef } from '../../types'
import StepNode, { type StepNodeData } from './StepNode'

const NODE_TYPES = { stepNode: StepNode }
const EDGE_OPTS = {
  markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
  style: { stroke: '#64748b', strokeWidth: 1.5 },
  type: 'smoothstep',
}
const H_GAP = 220
const V_GAP = 140

interface Props {
  definition: TemplateDef
  onChange: (def: TemplateDef) => void
}

// Derive which stage keys have predecessors
function computeRootKeys(stages: StageDef[]): Set<string> {
  const hasIncoming = new Set<string>()
  for (const stage of stages) {
    for (const crit of stage.entry_criteria) {
      if (crit.type === 'stage_complete' && crit.stage_key) {
        hasIncoming.add(stage.key)
      }
    }
  }
  return new Set(stages.filter((s) => !hasIncoming.has(s.key)).map((s) => s.key))
}

function stageToNode(
  stage: StageDef,
  idx: number,
  rootKeys: Set<string>,
  existingPositions: Map<string, { x: number; y: number }>
): Node<StepNodeData> {
  const pos = existingPositions.get(stage.key) ?? {
    x: (idx % 4) * H_GAP + 80,
    y: Math.floor(idx / 4) * V_GAP + 60,
  }
  return {
    id: stage.key,
    type: 'stepNode',
    position: pos,
    data: { stage, isRoot: rootKeys.has(stage.key) },
  }
}

function buildEdges(stages: StageDef[]): Edge[] {
  const edges: Edge[] = []
  for (const stage of stages) {
    for (const crit of stage.entry_criteria) {
      if (crit.type === 'stage_complete' && crit.stage_key) {
        edges.push({
          id: `${crit.stage_key}->${stage.key}`,
          source: crit.stage_key,
          target: stage.key,
          ...EDGE_OPTS,
        })
      }
    }
  }
  return edges
}

export default function FlowEditor({ definition, onChange }: Props) {
  // Track node positions across re-renders
  const [positions, setPositions] = useState<Map<string, { x: number; y: number }>>(new Map())

  const rootKeys = useMemo(() => computeRootKeys(definition.stages), [definition.stages])

  const initialNodes = useMemo(
    () => definition.stages.map((s, i) => stageToNode(s, i, rootKeys, positions)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [definition.stages]
  )
  const initialEdges = useMemo(() => buildEdges(definition.stages), [definition.stages])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // Sync when definition changes from outside (e.g. stage added/removed)
  useEffect(() => {
    const newRoots = computeRootKeys(definition.stages)
    setNodes(definition.stages.map((s, i) => stageToNode(s, i, newRoots, positions)))
    setEdges(buildEdges(definition.stages))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [definition.stages.length])

  // Persist positions when nodes are dragged
  const handleNodeDragStop: NodeMouseHandler = useCallback(
    (_evt, node) => {
      setPositions((prev) => new Map(prev).set(node.id, node.position))
    },
    []
  )

  // When user draws an edge: add stage_complete criterion to target stage
  const onConnect = useCallback(
    (connection: Connection) => {
      const { source, target } = connection
      if (!source || !target || source === target) return

      const updatedStages = definition.stages.map((stage) => {
        if (stage.key !== target) return stage
        // Avoid duplicate
        const alreadyHas = stage.entry_criteria.some(
          (c) => c.type === 'stage_complete' && c.stage_key === source
        )
        if (alreadyHas) return stage
        return {
          ...stage,
          entry_criteria: [
            ...stage.entry_criteria,
            { type: 'stage_complete', stage_key: source },
          ],
        }
      })
      onChange({ stages: updatedStages })
      setEdges((eds) => addEdge({ ...connection, ...EDGE_OPTS }, eds))
    },
    [definition.stages, onChange, setEdges]
  )

  // When user deletes an edge: remove the matching entry_criterion
  const onEdgeDelete = useCallback(
    (deletedEdges: Edge[]) => {
      let stages = [...definition.stages]
      for (const edge of deletedEdges) {
        stages = stages.map((stage) => {
          if (stage.key !== edge.target) return stage
          return {
            ...stage,
            entry_criteria: stage.entry_criteria.filter(
              (c) => !(c.type === 'stage_complete' && c.stage_key === edge.source)
            ),
          }
        })
      }
      onChange({ stages })
    },
    [definition.stages, onChange]
  )

  if (definition.stages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        Add stages in the Stages &amp; Tasks tab to see the flow diagram.
      </div>
    )
  }

  return (
    <div className="flex-1" style={{ height: '100%', minHeight: 400 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onEdgesDelete={onEdgeDelete}
        onNodeDragStop={handleNodeDragStop}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        deleteKeyCode="Delete"
      >
        <Background color="hsl(var(--border))" gap={20} />
        <Controls />
        <MiniMap
          nodeColor={(n) => (n.data.isRoot ? '#4ade80' : '#3b82f6')}
          pannable
          zoomable
        />
      </ReactFlow>
    </div>
  )
}
