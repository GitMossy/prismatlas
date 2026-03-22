import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../../store'
import { useAreas, useUnits } from '../../hooks/useProjects'
import { useProjectReadinessSummary } from '../../hooks/useReadiness'
import { useObjects } from '../../hooks/useObjects'
import { useHierarchyNodes, useCreateHierarchyNode, useHierarchyNodeMembers, DIMENSIONS, type Dimension } from '../../hooks/useHierarchy'
import { hierarchyApi } from '../../api/hierarchy'
import { getUnits } from '../../api/projects'
import { getObjects } from '../../api/objects'
import type { Area, Unit, ProjectObject, ProjectReadinessSummaryItem, HierarchyNode } from '../../types'

// ---------------------------------------------------------------------------
// Readiness score — coloured dot + percentage
// ---------------------------------------------------------------------------

function ReadinessScore({ readiness }: { readiness: number | null }) {
  if (readiness === null) {
    return <span className="text-xs text-muted-foreground tabular-nums">—</span>
  }
  const pct = Math.round(readiness * 100)
  const colour = readiness >= 0.9 ? 'text-green-400' : readiness >= 0.5 ? 'text-amber-400' : 'text-red-400'
  return <span className={`text-xs tabular-nums font-medium ${colour}`}>{pct}%</span>
}

function avgReadiness(ids: string[], summaryMap: Map<string, number>): number | null {
  const values = ids.map((id) => summaryMap.get(id)).filter((v): v is number => v !== undefined)
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null
}

// ---------------------------------------------------------------------------
// Object row — leaf level
// ---------------------------------------------------------------------------

function ObjectRow({
  obj,
  summaryMap,
}: {
  obj: ProjectObject
  summaryMap: Map<string, number>
}) {
  const { setSelectedEntity, selectedEntity } = useAppStore()
  const readiness = summaryMap.get(obj.id) ?? null
  const isSelected = selectedEntity?.id === obj.id

  return (
    <button
      className={`w-full text-left flex items-center justify-between px-2 py-1 text-xs rounded transition-colors
        ${isSelected ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent hover:text-foreground'}`}
      onClick={() => setSelectedEntity({ id: obj.id, type: 'object' })}
      title={obj.name}
    >
      <span className="truncate pl-6">{obj.name}</span>
      <ReadinessScore readiness={readiness} />
    </button>
  )
}

// ---------------------------------------------------------------------------
// Unit row — expandable
// ---------------------------------------------------------------------------

function UnitRow({
  unit,
  areaId,
  summary,
  summaryMap,
}: {
  unit: Unit
  areaId: string
  summary: ProjectReadinessSummaryItem[]
  summaryMap: Map<string, number>
}) {
  const [expanded, setExpanded] = useState(false)
  const { hierarchyContext, setHierarchyUnit, setSelectedEntity } = useAppStore()
  const { selectedProjectId } = useAppStore()
  const { data: objects = [] } = useObjects(selectedProjectId, undefined, { unit_id: unit.id })

  const unitIds = objects.map((o) => o.id)
  const unitReadiness = avgReadiness(unitIds, summaryMap)
  const isActive = hierarchyContext.unitId === unit.id

  const ems = objects.filter((o) => o.object_type === 'EM')
  const directCMs = objects.filter((o) => o.object_type === 'CM' && !o.parent_object_id)
  const hasChildren = ems.length > 0 || directCMs.length > 0

  // summary is passed down but not directly used here — consumed via summaryMap
  void summary

  return (
    <div>
      <div className="flex items-center">
        <button
          className="w-4 h-6 flex items-center justify-center text-muted-foreground hover:text-foreground shrink-0 text-xs"
          onClick={() => setExpanded((e) => !e)}
          disabled={!hasChildren}
          aria-label={expanded ? 'Collapse' : 'Expand'}
        >
          {hasChildren ? (expanded ? '▾' : '▸') : ''}
        </button>
        <button
          className={`flex-1 text-left flex items-center justify-between px-2 py-1.5 text-xs rounded transition-colors min-w-0
            ${isActive ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-accent'}`}
          onClick={() => {
            setHierarchyUnit(areaId, unit.id)
            setSelectedEntity(null)
          }}
          title={unit.name}
        >
          <span className="truncate pl-2">{unit.name}</span>
          <ReadinessScore readiness={unitReadiness} />
        </button>
      </div>

      {expanded && hasChildren && (
        <div className="ml-3">
          {ems.map((em) => (
            <ObjectRow key={em.id} obj={em} summaryMap={summaryMap} />
          ))}
          {directCMs.length > 0 && (
            <span className="block px-2 py-0.5 text-xs text-muted-foreground pl-8">
              {directCMs.length} direct CM{directCMs.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Area row — expandable
// ---------------------------------------------------------------------------

function AreaRow({
  area,
  summary,
  summaryMap,
}: {
  area: Area
  summary: ProjectReadinessSummaryItem[]
  summaryMap: Map<string, number>
}) {
  const [expanded, setExpanded] = useState(false)
  const { hierarchyContext, setHierarchyArea, setSelectedEntity } = useAppStore()
  const { selectedProjectId } = useAppStore()
  const { data: units = [] } = useUnits(expanded ? area.id : null)
  const { data: areaObjects = [] } = useObjects(selectedProjectId, undefined, { area_id: area.id })

  const areaIds = areaObjects.map((o) => o.id)
  const areaReadiness = avgReadiness(areaIds, summaryMap)
  const isAreaActive = hierarchyContext.areaId === area.id && !hierarchyContext.unitId

  return (
    <div>
      <div className="flex items-center">
        <button
          className="w-4 h-6 flex items-center justify-center text-muted-foreground hover:text-foreground shrink-0 text-xs"
          onClick={() => setExpanded((e) => !e)}
          aria-label={expanded ? 'Collapse' : 'Expand'}
        >
          {expanded ? '▾' : '▸'}
        </button>
        <button
          className={`flex-1 text-left flex items-center justify-between px-2 py-1.5 text-xs rounded transition-colors min-w-0
            ${isAreaActive ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-accent'}`}
          onClick={() => {
            setHierarchyArea(area.id)
            setSelectedEntity(null)
          }}
          title={area.name}
        >
          <span className="truncate font-medium">{area.name}</span>
          <ReadinessScore readiness={areaReadiness} />
        </button>
      </div>

      {expanded && (
        <div className="ml-3">
          {units.length === 0 ? (
            <p className="text-xs text-muted-foreground px-3 py-1">No units</p>
          ) : (
            units.map((u) => (
              <UnitRow
                key={u.id}
                unit={u}
                areaId={area.id}
                summary={summary}
                summaryMap={summaryMap}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hierarchy Nodes tree (C3 — unlimited-depth)
// ---------------------------------------------------------------------------

interface AddNodeProps {
  adding: string | null
  newName: string
  setNewName: (v: string) => void
  setAdding: (v: string | null) => void
  handleAddNode: (parentId: string | null) => Promise<void>
}

function InlineAddInput({
  parentId,
  addProps,
}: {
  parentId: string | null
  addProps: AddNodeProps
}) {
  const { newName, setNewName, setAdding, handleAddNode } = addProps
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  return (
    <input
      ref={inputRef}
      value={newName}
      onChange={(e) => setNewName(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter') handleAddNode(parentId)
        if (e.key === 'Escape') { setAdding(null); setNewName('') }
      }}
      onBlur={() => { setAdding(null); setNewName('') }}
      placeholder="Node name…"
      className="flex-1 bg-input border border-ring rounded px-2 py-0.5 text-xs text-foreground outline-none min-w-0"
    />
  )
}

const OBJECT_TYPE_ICON: Record<string, string> = {
  EM: 'EM',
  CM: 'CM',
  Phase: 'PH',
  IO: 'IO',
}

function HierarchyNodeRow({
  node,
  depth,
  addProps,
}: {
  node: HierarchyNode
  depth: number
  addProps: AddNodeProps
}) {
  const [expanded, setExpanded] = useState(false)
  const { setHierarchyNode, hierarchyNodeId, setSelectedEntity, selectedEntity } = useAppStore()
  const { adding, setAdding, setNewName } = addProps
  const { data: members = [] } = useHierarchyNodeMembers(expanded ? node.id : null)

  const isActive = hierarchyNodeId === node.id

  return (
    <div>
      <div className="flex items-center group">
        <button
          className="w-4 h-6 flex items-center justify-center text-muted-foreground hover:text-foreground shrink-0 text-xs"
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? '▾' : '▸'}
        </button>
        <button
          className={`flex-1 text-left flex items-center px-2 py-1 text-xs rounded transition-colors min-w-0
            ${isActive ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-accent'}`}
          style={{ paddingLeft: `${depth * 8 + 8}px` }}
          onClick={() => setHierarchyNode(node.id)}
          title={node.name}
        >
          <span className="truncate">{node.name}</span>
        </button>
        <button
          className="opacity-0 group-hover:opacity-100 px-1 text-muted-foreground hover:text-foreground text-xs shrink-0 transition-opacity"
          title="Add child node"
          onMouseDown={(e) => {
            e.preventDefault()
            setExpanded(true)
            setAdding(node.id)
            setNewName('')
          }}
        >
          +
        </button>
      </div>
      {expanded && (
        <div className="ml-4">
          {adding === node.id && (
            <div className="flex items-center px-1 py-0.5">
              <InlineAddInput parentId={node.id} addProps={addProps} />
            </div>
          )}
          {node.children.map((child) => (
            <HierarchyNodeRow key={child.id} node={child} depth={depth + 1} addProps={addProps} />
          ))}
          {members.map((m) => {
            const isSel = selectedEntity?.id === m.entity_id
            const icon = m.object_type ? (OBJECT_TYPE_ICON[m.object_type] ?? m.object_type) : '—'
            return (
              <button
                key={m.entity_id}
                className={`w-full text-left flex items-center gap-1.5 px-2 py-1 text-xs rounded transition-colors
                  ${isSel ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent hover:text-foreground'}`}
                style={{ paddingLeft: `${(depth + 1) * 8 + 8}px` }}
                onClick={() => setSelectedEntity({ id: m.entity_id, type: 'object' })}
                title={m.name}
              >
                <span className="text-muted-foreground font-mono shrink-0">{icon}</span>
                <span className="truncate">{m.name}</span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

function HierarchyNodesTree({
  projectId,
  areas,
}: {
  projectId: string
  areas: Area[]
}) {
  const [dimension, setDimension] = useState<Dimension>('ZBS')
  const [adding, setAdding] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [seeding, setSeeding] = useState(false)
  const { data: nodes = [], isLoading } = useHierarchyNodes(projectId, dimension)
  const createNode = useCreateHierarchyNode(projectId)

  async function handleAddNode(parentId: string | null) {
    if (!newName.trim()) return
    await createNode.mutateAsync({
      dimension,
      name: newName.trim(),
      parent_id: parentId,
      position: 0,
    })
    setNewName('')
    setAdding(null)
  }

  async function seedFromAreas() {
    if (seeding || areas.length === 0) return
    setSeeding(true)
    try {
      for (const [i, area] of areas.entries()) {
        const areaNode = await createNode.mutateAsync({
          dimension: 'ZBS',
          name: area.name,
          parent_id: null,
          position: i,
        })
        const units = await getUnits(area.id)
        for (const [j, unit] of units.entries()) {
          const unitNode = await createNode.mutateAsync({
            dimension: 'ZBS',
            name: unit.name,
            parent_id: areaNode.id,
            position: j,
          })
          const objects = await getObjects({ project_id: projectId, unit_id: unit.id })
          for (const obj of objects) {
            await hierarchyApi.addMember(unitNode.id, { entity_type: 'object', entity_id: obj.id })
          }
        }
      }
      setDimension('ZBS')
    } finally {
      setSeeding(false)
    }
  }

  const addProps: AddNodeProps = { adding, newName, setNewName, setAdding, handleAddNode }

  return (
    <div>
      <div className="flex items-center gap-1 px-2 pt-2 pb-1">
        <p className="text-xs uppercase text-muted-foreground tracking-wider">Hierarchy</p>
        <select
          value={dimension}
          onChange={(e) => setDimension(e.target.value as Dimension)}
          className="ml-auto bg-background border border-border rounded px-1 py-0.5 text-xs text-foreground"
        >
          {DIMENSIONS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <button
          className="px-1 text-muted-foreground hover:text-foreground text-xs shrink-0"
          title="Add root node"
          onClick={() => { setAdding('root'); setNewName('') }}
        >
          +
        </button>
      </div>
      {isLoading && <p className="text-xs text-muted-foreground px-4 py-1">Loading…</p>}
      {!isLoading && nodes.length === 0 && adding !== 'root' && (
        <div className="px-4 py-1 flex flex-col gap-1">
          <p className="text-xs text-muted-foreground">No nodes</p>
          {dimension === 'ZBS' && areas.length > 0 && (
            <button
              className="text-xs text-primary hover:text-primary/80 text-left disabled:opacity-50"
              onClick={seedFromAreas}
              disabled={seeding}
            >
              {seeding ? 'Seeding…' : 'Seed from Areas'}
            </button>
          )}
        </div>
      )}
      <div className="px-2 space-y-0.5">
        {adding === 'root' && (
          <div className="flex items-center px-1 py-0.5">
            <InlineAddInput parentId={null} addProps={addProps} />
          </div>
        )}
        {nodes.map((node) => (
          <HierarchyNodeRow key={node.id} node={node} depth={0} addProps={addProps} />
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Root
// ---------------------------------------------------------------------------

export default function HierarchyTree() {
  const { selectedProjectId } = useAppStore()
  const [mode, setMode] = useState<'legacy' | 'nodes'>('legacy')
  const { data: areas = [], isLoading } = useAreas(selectedProjectId)
  const { data: summary = [] } = useProjectReadinessSummary(selectedProjectId)

  const summaryMap = new Map<string, number>(
    summary.map((s) => [s.entity_id, s.overall_readiness])
  )

  return (
    <div className="flex flex-col">
      {/* Mode toggle */}
      <div className="flex px-2 pt-2 gap-1">
        <button
          onClick={() => setMode('legacy')}
          className={`flex-1 text-xs py-0.5 rounded transition-colors ${
            mode === 'legacy' ? 'bg-accent text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Areas
        </button>
        <button
          onClick={() => setMode('nodes')}
          className={`flex-1 text-xs py-0.5 rounded transition-colors ${
            mode === 'nodes' ? 'bg-accent text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Hierarchy
        </button>
      </div>

      {mode === 'legacy' && (
        <div className="px-2 py-2 space-y-0.5">
          <p className="text-xs uppercase text-muted-foreground tracking-wider px-2 pb-1">Areas / Units</p>
          {isLoading && <p className="text-xs text-muted-foreground px-2 py-2">Loading…</p>}
          {!isLoading && areas.length === 0 && <p className="text-xs text-muted-foreground px-2 py-2">No areas</p>}
          {areas.map((a) => (
            <AreaRow key={a.id} area={a} summary={summary} summaryMap={summaryMap} />
          ))}
        </div>
      )}

      {mode === 'nodes' && selectedProjectId && (
        <HierarchyNodesTree projectId={selectedProjectId} areas={areas} />
      )}
    </div>
  )
}
