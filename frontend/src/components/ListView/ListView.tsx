import { useState, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { TbChevronDown, TbChevronRight, TbPlus, TbFolderOpen, TbFolder } from 'react-icons/tb'
import { useAppStore } from '../../store'
import { useObjects, useDocuments } from '../../hooks/useObjects'
import { deleteObject } from '../../api/objects'
import { hierarchyApi, getProjectHierarchyMemberships } from '../../api/hierarchy'
import type { NodeMembership } from '../../api/hierarchy'
import ObjectFormModal from '../ObjectFormModal/ObjectFormModal'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import type { ProjectObject, Document, HierarchyNode } from '../../types'

// ── Status helpers ──────────────────────────────────────────────────────────

const STATUS_BADGE_VARIANT: Record<string, 'default' | 'secondary' | 'ready' | 'warning' | 'blocked' | 'outline'> = {
  not_started: 'secondary',
  in_progress: 'default',
  blocked:     'blocked',
  complete:    'ready',
  Draft:       'secondary',
  In_Review:   'warning',
  Approved:    'ready',
  Superseded:  'outline',
}

const STATUS_LABELS: Record<string, string> = {
  not_started: 'Not Started',
  in_progress: 'In Progress',
  blocked:     'Blocked',
  complete:    'Complete',
}

function StatusBadge({ status }: { status: string }) {
  return <Badge variant={STATUS_BADGE_VARIANT[status] ?? 'secondary'}>{STATUS_LABELS[status] ?? status}</Badge>
}

// ── Table constants ─────────────────────────────────────────────────────────

const COL_HEADERS = ['Name', 'Type', 'Status', 'Zone', 'Owner', '']
const COL_SPAN = COL_HEADERS.length

// ── Object row ──────────────────────────────────────────────────────────────

function ObjectRow({
  obj,
  depth = 0,
  onEdit,
  onDelete,
}: {
  obj: ProjectObject
  depth?: number
  onEdit: (obj: ProjectObject) => void
  onDelete: (obj: ProjectObject) => void
}) {
  const { setSelectedEntity } = useAppStore()
  return (
    <tr className="border-t border-border hover:bg-accent/40">
      <td
        className="py-2 px-4 text-sm text-foreground cursor-pointer"
        style={{ paddingLeft: `${depth * 20 + 16}px` }}
        onClick={() => setSelectedEntity({ id: obj.id, type: 'object' })}
      >
        {obj.name}
      </td>
      <td className="py-2 px-4 text-xs text-muted-foreground">{obj.object_type}</td>
      <td className="py-2 px-4"><StatusBadge status={obj.status} /></td>
      <td className="py-2 px-4 text-xs text-muted-foreground">{obj.zone ?? '—'}</td>
      <td className="py-2 px-4 text-xs text-muted-foreground">{obj.owner ?? '—'}</td>
      <td className="py-2 px-4">
        <div className="flex gap-2 justify-end">
          <button onClick={(e) => { e.stopPropagation(); onEdit(obj) }} className="text-xs text-primary hover:underline">Edit</button>
          <button onClick={(e) => { e.stopPropagation(); onDelete(obj) }} className="text-xs text-red-500 hover:underline">Delete</button>
        </div>
      </td>
    </tr>
  )
}

// ── Document row ────────────────────────────────────────────────────────────

function DocumentRow({ doc }: { doc: Document }) {
  const { setSelectedEntity } = useAppStore()
  return (
    <tr className="border-t border-border hover:bg-accent/40 cursor-pointer" onClick={() => setSelectedEntity({ id: doc.id, type: 'document' })}>
      <td className="py-2 px-4 text-sm text-foreground">{doc.name}</td>
      <td className="py-2 px-4 text-xs text-muted-foreground">{doc.document_type}</td>
      <td className="py-2 px-4"><StatusBadge status={doc.status} /></td>
      <td className="py-2 px-4 text-xs text-muted-foreground">—</td>
      <td className="py-2 px-4 text-xs text-muted-foreground">—</td>
      <td className="py-2 px-4" />
    </tr>
  )
}

// ── Delete confirm row ──────────────────────────────────────────────────────

function DeleteConfirmRow({ obj, onCancel, onConfirm, isPending }: {
  obj: ProjectObject; onCancel: () => void; onConfirm: () => void; isPending: boolean
}) {
  return (
    <tr className="bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800">
      <td colSpan={COL_SPAN} className="py-2 px-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-red-700 dark:text-red-400">Delete "{obj.name}"? This cannot be undone.</span>
          <div className="flex gap-2">
            <button onClick={onCancel} className="text-xs px-2 py-1 border border-border rounded text-foreground hover:bg-muted">Cancel</button>
            <button onClick={onConfirm} disabled={isPending} className="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50">
              {isPending ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </div>
      </td>
    </tr>
  )
}

// ── Node picker modal ───────────────────────────────────────────────────────

function NodePickerTree({
  nodes,
  depth,
  onSelect,
}: {
  nodes: HierarchyNode[]
  depth: number
  onSelect: (node: HierarchyNode) => void
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(nodes.map(n => n.id)))

  const toggle = (id: string) =>
    setExpanded(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s })

  return (
    <>
      {nodes.map(node => (
        <div key={node.id}>
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer hover:bg-accent group"
            style={{ paddingLeft: `${depth * 16 + 12}px` }}
          >
            {node.children.length > 0 ? (
              <button
                onClick={(e) => { e.stopPropagation(); toggle(node.id) }}
                className="text-muted-foreground hover:text-foreground shrink-0"
              >
                {expanded.has(node.id) ? <TbChevronDown size={14} /> : <TbChevronRight size={14} />}
              </button>
            ) : (
              <span className="w-3.5 shrink-0" />
            )}
            {expanded.has(node.id) ? (
              <TbFolderOpen size={15} className="text-amber-500 shrink-0" />
            ) : (
              <TbFolder size={15} className="text-amber-500 shrink-0" />
            )}
            <button
              onClick={() => onSelect(node)}
              className="text-sm text-foreground text-left flex-1 hover:text-primary transition-colors"
            >
              {node.name}
            </button>
          </div>
          {expanded.has(node.id) && node.children.length > 0 && (
            <NodePickerTree nodes={node.children} depth={depth + 1} onSelect={onSelect} />
          )}
        </div>
      ))}
    </>
  )
}

function NodePickerModal({ nodes, onSelect, onSkip, onClose }: {
  nodes: HierarchyNode[]
  onSelect: (node: HierarchyNode) => void
  onSkip: () => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-card border border-border rounded-lg shadow-xl w-80 max-h-[60vh] flex flex-col">
        <div className="px-4 py-3 border-b border-border shrink-0">
          <p className="text-sm font-semibold text-foreground">Add object to…</p>
          <p className="text-xs text-muted-foreground mt-0.5">Select the hierarchy node where this object belongs</p>
        </div>
        <div className="flex-1 overflow-auto py-2">
          {nodes.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">
              No hierarchy defined yet. Build it in Settings → Areas & Units.
            </p>
          ) : (
            <NodePickerTree nodes={nodes} depth={0} onSelect={onSelect} />
          )}
        </div>
        <div className="px-4 py-3 border-t border-border shrink-0 flex justify-between items-center">
          <button onClick={onSkip} className="text-xs text-muted-foreground hover:text-foreground">
            Skip — add without location
          </button>
          <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
        </div>
      </div>
    </div>
  )
}

// ── Hierarchy section (collapsible) ─────────────────────────────────────────

function HierarchySection({
  node,
  depth,
  objectsById,
  membersByNode,
  onEdit,
  onAddHere,
  deletingId,
  onDeleteRequest,
  onDeleteCancel,
  onDeleteConfirm,
  deletePending,
}: {
  node: HierarchyNode
  depth: number
  objectsById: Map<string, ProjectObject>
  membersByNode: Map<string, NodeMembership[]>
  onEdit: (obj: ProjectObject) => void
  onAddHere: (node: HierarchyNode) => void
  deletingId: string | null
  onDeleteRequest: (obj: ProjectObject) => void
  onDeleteCancel: () => void
  onDeleteConfirm: () => void
  deletePending: boolean
}) {
  const [expanded, setExpanded] = useState(depth === 0)
  const directMembers = (membersByNode.get(node.id) ?? [])
    .map(m => objectsById.get(m.entity_id))
    .filter((o): o is ProjectObject => !!o)

  const hasContent = node.children.length > 0 || directMembers.length > 0

  const bgClass = depth === 0
    ? 'bg-muted/60 border-b border-border'
    : depth === 1
    ? 'bg-muted/30 border-b border-border/60'
    : 'bg-muted/10 border-b border-border/40'

  return (
    <>
      {/* Section header */}
      <tr
        className={`cursor-pointer hover:bg-accent/30 transition-colors ${bgClass}`}
        onClick={() => setExpanded(e => !e)}
      >
        <td
          className="py-2 px-4 text-sm font-medium text-foreground"
          style={{ paddingLeft: `${depth * 20 + 16}px` }}
        >
          <span className="inline-flex items-center gap-2">
            {hasContent ? (
              expanded ? <TbChevronDown size={14} className="text-muted-foreground" /> : <TbChevronRight size={14} className="text-muted-foreground" />
            ) : (
              <span className="w-3.5" />
            )}
            {node.name}
            {directMembers.length > 0 && (
              <span className="text-xs text-muted-foreground font-normal">({directMembers.length})</span>
            )}
          </span>
        </td>
        <td colSpan={COL_SPAN - 2} />
        <td className="py-2 px-4 text-right">
          <button
            onClick={(e) => { e.stopPropagation(); onAddHere(node) }}
            className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity"
            title={`Add object to ${node.name}`}
          >
            <TbPlus size={12} /> Add
          </button>
        </td>
      </tr>

      {/* Children and objects when expanded */}
      {expanded && (
        <>
          {node.children.map(child => (
            <HierarchySection
              key={child.id}
              node={child}
              depth={depth + 1}
              objectsById={objectsById}
              membersByNode={membersByNode}
              onEdit={onEdit}
              onAddHere={onAddHere}
              deletingId={deletingId}
              onDeleteRequest={onDeleteRequest}
              onDeleteCancel={onDeleteCancel}
              onDeleteConfirm={onDeleteConfirm}
              deletePending={deletePending}
            />
          ))}
          {directMembers.map(obj => (
            <>
              <ObjectRow
                key={obj.id}
                obj={obj}
                depth={depth + 1}
                onEdit={onEdit}
                onDelete={onDeleteRequest}
              />
              {deletingId === obj.id && (
                <DeleteConfirmRow
                  key={`${obj.id}-confirm`}
                  obj={obj}
                  onCancel={onDeleteCancel}
                  onConfirm={onDeleteConfirm}
                  isPending={deletePending}
                />
              )}
            </>
          ))}
          {!hasContent && (
            <tr>
              <td
                colSpan={COL_SPAN}
                className="py-3 text-xs text-muted-foreground italic"
                style={{ paddingLeft: `${(depth + 1) * 20 + 16}px` }}
              >
                Empty — add objects here
              </td>
            </tr>
          )}
        </>
      )}
    </>
  )
}

// ── Main ListView ────────────────────────────────────────────────────────────

export default function ListView() {
  const { selectedProjectId } = useAppStore()
  const queryClient = useQueryClient()

  const { data: objects = [], isLoading: objLoading } = useObjects(selectedProjectId)
  const { data: documents = [], isLoading: docLoading } = useDocuments(selectedProjectId)

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

  const objectsById = useMemo(() => new Map(objects.map(o => [o.id, o])), [objects])

  const membersByNode = useMemo(() => {
    const map = new Map<string, NodeMembership[]>()
    for (const m of memberships) {
      if (!map.has(m.node_id)) map.set(m.node_id, [])
      map.get(m.node_id)!.push(m)
    }
    return map
  }, [memberships])

  const assignedEntityIds = useMemo(() => new Set(memberships.map(m => m.entity_id)), [memberships])

  const unassignedObjects = useMemo(
    () => objects.filter(o => !assignedEntityIds.has(o.id)),
    [objects, assignedEntityIds],
  )

  // Create + assign flow
  const [pickingNode, setPickingNode] = useState(false)
  const [targetNodeId, setTargetNodeId] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingObject, setEditingObject] = useState<ProjectObject | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const addMemberMutation = useMutation({
    mutationFn: ({ nodeId, entityId }: { nodeId: string; entityId: string }) =>
      hierarchyApi.addMember(nodeId, { entity_type: 'object', entity_id: entityId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hierarchy-memberships'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteObject(deletingId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['objects'] })
      queryClient.invalidateQueries({ queryKey: ['hierarchy-memberships'] })
      setDeletingId(null)
    },
  })

  const handleNodeSelected = (node: HierarchyNode) => {
    setTargetNodeId(node.id)
    setPickingNode(false)
    setShowCreateModal(true)
  }

  const handleSkipNode = () => {
    setTargetNodeId(null)
    setPickingNode(false)
    setShowCreateModal(true)
  }

  const handleCreateSuccess = (obj: ProjectObject) => {
    if (targetNodeId) {
      addMemberMutation.mutate({ nodeId: targetNodeId, entityId: obj.id })
    }
    queryClient.invalidateQueries({ queryKey: ['objects'] })
    setTargetNodeId(null)
  }

  const deleteProps = {
    deletingId,
    onDeleteRequest: (obj: ProjectObject) => setDeletingId(obj.id),
    onDeleteCancel: () => setDeletingId(null),
    onDeleteConfirm: () => deleteMutation.mutate(),
    deletePending: deleteMutation.isPending,
  }

  if (!selectedProjectId) return null
  if (objLoading || docLoading || hierarchyLoading || membershipsLoading) {
    return <div className="flex-1 flex items-center justify-center text-muted-foreground">Loading…</div>
  }

  return (
    <div className="flex-1 overflow-auto p-6 bg-muted/30 space-y-6">

      {/* Objects section */}
      <div className="bg-card rounded-lg border border-border overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 bg-muted/50 border-b border-border">
          <div>
            <h2 className="text-sm font-medium text-foreground">Objects ({objects.length})</h2>
            {hierarchyNodes.length > 0 && (
              <p className="text-xs text-muted-foreground mt-0.5">Organised by project structure</p>
            )}
          </div>
          <Button size="sm" className="h-7 text-xs gap-1" onClick={() => setPickingNode(true)}>
            <TbPlus size={13} /> New Object
          </Button>
        </div>

        <table className="w-full">
          <thead className="text-xs text-muted-foreground uppercase tracking-wide border-b border-border bg-muted/30">
            <tr>
              {COL_HEADERS.map((h, i) => (
                <th key={i} className="text-left py-2 px-4">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {hierarchyNodes.length === 0 ? (
              /* No hierarchy — flat list */
              objects.length === 0 ? (
                <tr><td colSpan={COL_SPAN} className="py-8 text-center text-sm text-muted-foreground">No objects yet. Click New Object to add one.</td></tr>
              ) : (
                objects.map(obj => (
                  <>
                    <ObjectRow key={obj.id} obj={obj} onEdit={setEditingObject} onDelete={deleteProps.onDeleteRequest} />
                    {deletingId === obj.id && (
                      <DeleteConfirmRow key={`${obj.id}-confirm`} obj={obj} onCancel={deleteProps.onDeleteCancel} onConfirm={deleteProps.onDeleteConfirm} isPending={deleteProps.deletePending} />
                    )}
                  </>
                ))
              )
            ) : (
              /* Hierarchy tree */
              <>
                {hierarchyNodes.map(node => (
                  <HierarchySection
                    key={node.id}
                    node={node}
                    depth={0}
                    objectsById={objectsById}
                    membersByNode={membersByNode}
                    onEdit={setEditingObject}
                    onAddHere={(node) => { setTargetNodeId(node.id); setShowCreateModal(true) }}
                    {...deleteProps}
                  />
                ))}

                {/* Unassigned objects */}
                {unassignedObjects.length > 0 && (
                  <>
                    <tr className="bg-muted/40 border-b border-border">
                      <td colSpan={COL_SPAN} className="py-2 px-4 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Unassigned ({unassignedObjects.length})
                      </td>
                    </tr>
                    {unassignedObjects.map(obj => (
                      <>
                        <ObjectRow key={obj.id} obj={obj} depth={1} onEdit={setEditingObject} onDelete={deleteProps.onDeleteRequest} />
                        {deletingId === obj.id && (
                          <DeleteConfirmRow key={`${obj.id}-confirm`} obj={obj} onCancel={deleteProps.onDeleteCancel} onConfirm={deleteProps.onDeleteConfirm} isPending={deleteProps.deletePending} />
                        )}
                      </>
                    ))}
                  </>
                )}
              </>
            )}
          </tbody>
        </table>
      </div>

      {/* Documents section */}
      <div className="bg-card rounded-lg border border-border overflow-hidden">
        <div className="px-4 py-3 bg-muted/50 border-b border-border">
          <h2 className="text-sm font-medium text-foreground">Documents ({documents.length})</h2>
        </div>
        <table className="w-full">
          <thead className="text-xs text-muted-foreground uppercase tracking-wide border-b border-border bg-muted/30">
            <tr>
              {COL_HEADERS.map((h, i) => <th key={i} className="text-left py-2 px-4">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {documents.length === 0
              ? <tr><td colSpan={COL_SPAN} className="py-6 text-center text-sm text-muted-foreground">No documents</td></tr>
              : documents.map(d => <DocumentRow key={d.id} doc={d} />)}
          </tbody>
        </table>
      </div>

      {/* Node picker modal */}
      {pickingNode && (
        <NodePickerModal
          nodes={hierarchyNodes}
          onSelect={handleNodeSelected}
          onSkip={handleSkipNode}
          onClose={() => setPickingNode(false)}
        />
      )}

      {/* Create modal */}
      {showCreateModal && (
        <ObjectFormModal
          mode="create"
          projectId={selectedProjectId}
          onClose={() => { setShowCreateModal(false); setTargetNodeId(null) }}
          onSuccess={handleCreateSuccess}
        />
      )}

      {/* Edit modal */}
      {editingObject && (
        <ObjectFormModal
          mode="edit"
          projectId={selectedProjectId}
          initialValues={editingObject}
          onClose={() => setEditingObject(null)}
          onSuccess={() => queryClient.invalidateQueries({ queryKey: ['objects'] })}
        />
      )}
    </div>
  )
}
