import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import { useProjectReadinessSummary } from '../../hooks/useReadiness'
import { useObjects } from '../../hooks/useObjects'
import { useSliceQuery } from '../../hooks/useSlice'
import { hierarchyApi, getProjectHierarchyMemberships } from '../../api/hierarchy'
import { Card } from '../ui/card'
import type { ProjectReadinessSummaryItem, ProjectObject, HierarchyNode } from '../../types'
import type { NodeMembership } from '../../api/hierarchy'

// ---- Shared UI atoms ----

// @ts-ignore -- used in future readiness panel
function ReadinessBar({ value, compact }: { value: number; compact?: boolean }) {
  const pct = Math.round(value * 100)
  const colour = value >= 0.9 ? 'bg-green-500' : value >= 0.5 ? 'bg-amber-400' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className={`flex-1 bg-muted rounded-full ${compact ? 'h-1.5' : 'h-2'}`}>
        <div className={`${colour} ${compact ? 'h-1.5' : 'h-2'} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground w-9 text-right">{pct}%</span>
    </div>
  )
}

function SummaryCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card className="p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-3xl font-semibold text-foreground mt-1">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </Card>
  )
}

// ---- Stage distribution ----

const STAGE_ORDER = [
  { key: 'engineering',   name: 'Engineering',   color: 'bg-gray-400' },
  { key: 'fat_prep',      name: 'FAT Prep',      color: 'bg-blue-400' },
  { key: 'fat_execution', name: 'FAT Execution', color: 'bg-amber-400' },
  { key: 'sat_prep',      name: 'SAT Prep',      color: 'bg-purple-400' },
  { key: 'sat_execution', name: 'SAT Execution', color: 'bg-green-500' },
]

function StageDistribution({ stageCounts, total }: { stageCounts: Record<string, number>; total: number }) {
  if (total === 0) return <p className="text-sm text-muted-foreground">No stage data.</p>

  const known = new Set(STAGE_ORDER.map(s => s.key))
  const other = Object.entries(stageCounts)
    .filter(([k]) => !known.has(k))
    .reduce((sum, [, v]) => sum + v, 0)

  const rows = [...STAGE_ORDER.map(s => ({ ...s, count: stageCounts[s.key] ?? 0 })),
    ...(other > 0 ? [{ key: 'other', name: 'Other', color: 'bg-muted-foreground/40', count: other }] : []),
  ].filter(r => r.count > 0)

  return (
    <div className="space-y-2">
      {rows.map(row => (
        <div key={row.key} className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground w-28 shrink-0">{row.name}</span>
          <div className="flex-1 bg-muted rounded-full h-3 overflow-hidden">
            <div
              className={`${row.color} h-3 rounded-full`}
              style={{ width: `${(row.count / total) * 100}%` }}
            />
          </div>
          <span className="text-xs text-muted-foreground w-16 text-right shrink-0">
            {row.count} ({Math.round((row.count / total) * 100)}%)
          </span>
        </div>
      ))}
    </div>
  )
}

// ---- Coming Due ----

function ComingDue({
  items,
  onSelect,
}: {
  items: Array<ProjectObject & { readiness: ProjectReadinessSummaryItem | null }>
  onSelect: (id: string) => void
}) {
  if (items.length === 0) return <p className="text-sm text-muted-foreground">No objects due in the next 30 days.</p>

  const today = new Date()

  return (
    <div className="space-y-1">
      {items.map(obj => {
        const isOverdue = obj.planned_end ? new Date(obj.planned_end) < today : false
        const readinessPct = obj.readiness ? Math.round(obj.readiness.overall_readiness * 100) : null
        const colour = readinessPct == null ? 'bg-muted' : readinessPct >= 90 ? 'bg-green-500' : readinessPct >= 50 ? 'bg-amber-400' : 'bg-red-500'

        return (
          <button
            key={obj.id}
            onClick={() => onSelect(obj.id)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded hover:bg-accent/40 text-left"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{obj.name}</p>
              <p className="text-xs text-muted-foreground">{obj.zone ?? '—'}</p>
            </div>
            <span className="text-xs text-muted-foreground shrink-0">{obj.planned_end}</span>
            {isOverdue && (
              <span className="text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-1.5 py-0.5 rounded shrink-0">
                Overdue
              </span>
            )}
            {readinessPct != null && (
              <div className="flex items-center gap-1 shrink-0 w-20">
                <div className="flex-1 bg-muted rounded-full h-1.5">
                  <div className={`${colour} h-1.5 rounded-full`} style={{ width: `${readinessPct}%` }} />
                </div>
                <span className="text-xs text-muted-foreground w-7 text-right">{readinessPct}%</span>
              </div>
            )}
          </button>
        )
      })}
    </div>
  )
}

// ---- Helpers ----

function statusCompletion(status: string | null | undefined): number {
  if (status === 'complete') return 1
  if (status === 'in_progress') return 0.5
  return 0
}

function buildNodeCompletionMap(
  nodes: HierarchyNode[],
  membersByNode: Map<string, NodeMembership[]>,
): Map<string, { completion: number; total: number; complete: number }> {
  const result = new Map<string, { completion: number; total: number; complete: number }>()

  function compute(node: HierarchyNode): number {
    const direct = membersByNode.get(node.id) ?? []
    const directVals = direct.map(m => statusCompletion(m.status))
    const childVals = node.children.map(compute)
    const allVals = [...directVals, ...childVals]
    const completion = allVals.length ? allVals.reduce((a, b) => a + b, 0) / allVals.length : 0
    const complete = direct.filter(m => m.status === 'complete').length
    result.set(node.id, { completion, total: direct.length, complete })
    return completion
  }

  nodes.forEach(compute)
  return result
}

// ---- Object leaf row ----

function ObjectLeafRow({
  member,
  depth,
  onSelectObject,
}: {
  member: NodeMembership
  depth: number
  onSelectObject: (id: string) => void
}) {
  const completion = statusCompletion(member.status)
  const colour = completion >= 1 ? 'bg-green-500' : completion > 0 ? 'bg-amber-400' : 'bg-muted-foreground/30'
  const statusLabel: Record<string, string> = {
    complete: 'Complete', in_progress: 'In Progress', blocked: 'Blocked', not_started: 'Not Started',
  }

  return (
    <tr
      className="border-t border-border/50 hover:bg-primary/5 cursor-pointer"
      onClick={() => onSelectObject(member.entity_id)}
    >
      <td className="py-1.5 px-4 text-sm text-foreground" style={{ paddingLeft: `${depth * 20 + 16}px` }}>
        <span className="text-xs text-muted-foreground mr-2">{member.object_type}</span>
        {member.name}
      </td>
      <td className="py-1.5 px-4 text-center text-xs text-muted-foreground">1</td>
      <td className="py-1.5 px-4 w-44">
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-muted rounded-full h-1.5">
            <div className={`${colour} h-1.5 rounded-full`} style={{ width: `${Math.round(completion * 100)}%` }} />
          </div>
          <span className="text-xs text-muted-foreground w-9 text-right">{Math.round(completion * 100)}%</span>
        </div>
      </td>
      <td className="py-1.5 px-4 text-center text-xs text-muted-foreground">
        {statusLabel[member.status ?? ''] ?? member.status ?? '—'}
      </td>
    </tr>
  )
}

// ---- Hierarchy node row (recursive) ----

function HierarchyNodeRow({
  node,
  depth,
  membersByNode,
  completionMap,
  onSelectObject,
}: {
  node: HierarchyNode
  depth: number
  membersByNode: Map<string, NodeMembership[]>
  completionMap: Map<string, { completion: number; total: number; complete: number }>
  onSelectObject: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(depth === 0)
  const stats = completionMap.get(node.id) ?? { completion: 0, total: 0, complete: 0 }
  const direct = membersByNode.get(node.id) ?? []
  const hasChildren = node.children.length > 0 || direct.length > 0

  const pct = Math.round(stats.completion * 100)
  const colour = pct >= 100 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-500'
  const bgDepth = depth === 0 ? 'bg-card hover:bg-accent/20' : depth === 1 ? 'bg-muted/20 hover:bg-muted/40' : 'bg-muted/10 hover:bg-muted/30'

  return (
    <>
      <tr
        className={`border-t border-border cursor-pointer transition-colors ${bgDepth}`}
        onClick={() => setExpanded(e => !e)}
      >
        <td className="py-2 px-4 text-sm font-medium text-foreground" style={{ paddingLeft: `${depth * 20 + 16}px` }}>
          {hasChildren && (
            <span className="mr-2 text-muted-foreground text-xs">{expanded ? '▼' : '▶'}</span>
          )}
          {node.name}
        </td>
        <td className="py-2 px-4 text-center text-sm text-muted-foreground">{stats.total}</td>
        <td className="py-2 px-4 w-44">
          <div className="flex items-center gap-2">
            <div className={`flex-1 bg-muted rounded-full ${depth === 0 ? 'h-2' : 'h-1.5'}`}>
              <div
                className={`${colour} ${depth === 0 ? 'h-2' : 'h-1.5'} rounded-full transition-all`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground w-9 text-right">{pct}%</span>
          </div>
        </td>
        <td className="py-2 px-4 text-center text-xs text-muted-foreground">
          {stats.total > 0 ? `${stats.complete}/${stats.total}` : '—'}
        </td>
      </tr>

      {expanded && (
        <>
          {node.children.map(child => (
            <HierarchyNodeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              membersByNode={membersByNode}
              completionMap={completionMap}
              onSelectObject={onSelectObject}
            />
          ))}
          {direct.map(m => (
            <ObjectLeafRow
              key={m.entity_id}
              member={m}
              depth={depth + 1}
              onSelectObject={onSelectObject}
            />
          ))}
        </>
      )}
    </>
  )
}

// ---- Main Dashboard ----

export default function Dashboard() {
  const { selectedProjectId, setSelectedEntity } = useAppStore()

  const { data: summary = [], isLoading: summaryLoading } = useProjectReadinessSummary(selectedProjectId)
  const { data: objects = [] } = useObjects(selectedProjectId)
  const { data: sliceData } = useSliceQuery(selectedProjectId, {})

  const { data: hierarchyNodes = [], isLoading: hierarchyLoading } = useQuery({
    queryKey: ['hierarchy-nodes', selectedProjectId, 'ZBS'],
    queryFn: () => hierarchyApi.listNodes(selectedProjectId!, 'ZBS'),
    enabled: !!selectedProjectId,
  })

  const { data: memberships = [], isLoading: membershipsLoading } = useQuery({
    queryKey: ['hierarchy-memberships', selectedProjectId, 'ZBS'],
    queryFn: () => getProjectHierarchyMemberships(selectedProjectId!, 'ZBS'),
    enabled: !!selectedProjectId,
  })

  const membersByNode = useMemo(() => {
    const map = new Map<string, NodeMembership[]>()
    for (const m of memberships) {
      const key = m.node_id
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(m)
    }
    return map
  }, [memberships])

  const completionMap = useMemo(
    () => buildNodeCompletionMap(hierarchyNodes, membersByNode),
    [hierarchyNodes, membersByNode],
  )

  const isLoading = summaryLoading || hierarchyLoading || membershipsLoading

  const readinessMap = useMemo(
    () => new Map(summary.map(item => [item.entity_id, item])),
    [summary],
  )

  const objectSummary = useMemo(
    () => summary.filter(s => s.entity_type === 'object'),
    [summary],
  )

  const totalObjects = objectSummary.length
  const fatReady = objectSummary.filter(s => s.ready_for_fat).length
  const satReady = objectSummary.filter(s => s.ready_for_sat).length
  const totalBlockers = objectSummary.reduce((n, s) => n + s.blocker_count, 0)
  const avgReadiness = totalObjects
    ? Math.round((objectSummary.reduce((n, s) => n + s.overall_readiness, 0) / totalObjects) * 100)
    : 0

  const stageCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const item of sliceData?.results ?? []) {
      const stage = item.current_stage ?? 'unknown'
      counts[stage] = (counts[stage] ?? 0) + 1
    }
    return counts
  }, [sliceData])

  const comingDue = useMemo(() => {
    const today = new Date()
    const cutoff = new Date(today)
    cutoff.setDate(cutoff.getDate() + 30)
    return objects
      .filter(o => o.planned_end && new Date(o.planned_end) <= cutoff)
      .map(o => ({ ...o, readiness: readinessMap.get(o.id) ?? null }))
      .sort((a, b) => new Date(a.planned_end!).getTime() - new Date(b.planned_end!).getTime())
      .slice(0, 10)
  }, [objects, readinessMap])

  const handleSelectObject = (id: string) => {
    setSelectedEntity({ id, type: 'object' })
  }

  if (!selectedProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Select a project to view the dashboard.
      </div>
    )
  }

  if (isLoading) {
    return <div className="flex-1 flex items-center justify-center text-muted-foreground">Loading…</div>
  }

  return (
    <div className="flex-1 overflow-auto p-6 bg-muted/30 space-y-6">

      {/* Section 1 — KPI Strip */}
      <div className="grid grid-cols-5 gap-4">
        <SummaryCard label="Overall Readiness" value={`${avgReadiness}%`} sub="avg across objects" />
        <SummaryCard label="Total Objects" value={totalObjects} sub="in project" />
        <SummaryCard label="FAT Ready" value={fatReady} sub={`of ${totalObjects} objects`} />
        <SummaryCard label="SAT Ready" value={satReady} sub={`of ${totalObjects} objects`} />
        <SummaryCard label="Active Blockers" value={totalBlockers} sub="across all objects" />
      </div>

      {/* Section 2 — Project Structure */}
      {hierarchyNodes.length === 0 ? (
        <div className="bg-card rounded-lg border border-border px-6 py-10 text-center text-muted-foreground">
          No project structure defined yet.{' '}
          <span className="text-primary">Build the hierarchy in Settings → Areas & Units.</span>
        </div>
      ) : (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="px-4 py-3 border-b border-border bg-muted/50">
            <h2 className="text-sm font-semibold text-foreground">Project Structure</h2>
            <p className="text-xs text-muted-foreground mt-0.5">Completion rolls up from assigned objects through the hierarchy</p>
          </div>
          <table className="w-full">
            <thead className="bg-muted/50 text-xs text-muted-foreground uppercase tracking-wide border-b border-border">
              <tr>
                <th className="text-left py-2 px-4">Node</th>
                <th className="text-center py-2 px-4">Objects</th>
                <th className="text-left py-2 px-4">Completion</th>
                <th className="text-center py-2 px-4">Done / Total</th>
              </tr>
            </thead>
            <tbody>
              {hierarchyNodes.map(node => (
                <HierarchyNodeRow
                  key={node.id}
                  node={node}
                  depth={0}
                  membersByNode={membersByNode}
                  completionMap={completionMap}
                  onSelectObject={handleSelectObject}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Section 3 — Bottom row */}
      <div className="flex gap-4">
        <div className="bg-card rounded-lg border border-border p-5" style={{ flex: '2 1 0' }}>
          <h2 className="text-sm font-semibold text-foreground mb-3">Stage Distribution</h2>
          <StageDistribution stageCounts={stageCounts} total={sliceData?.total ?? 0} />
        </div>

        <div className="bg-card rounded-lg border border-border p-5" style={{ flex: '3 1 0' }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-foreground">
              Coming Due <span className="font-normal text-muted-foreground">(≤30 days)</span>
            </h2>
            {comingDue.length >= 10 && (
              <span className="text-xs text-primary">See all in List View</span>
            )}
          </div>
          <ComingDue items={comingDue} onSelect={handleSelectObject} />
        </div>
      </div>

    </div>
  )
}
