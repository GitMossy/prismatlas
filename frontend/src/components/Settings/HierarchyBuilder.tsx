/**
 * HierarchyBuilder — unlimited-depth drag-and-drop tree editor.
 *
 * Uses the HierarchyNode API (ZBS dimension by default).
 * Both "Folder" and "Unit" palette items can be dropped:
 *   • On the root zone  → creates a top-level node
 *   • On any tree node  → creates a child of that node
 * Any node can contain children regardless of its type.
 */
import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  TbChevronDown,
  TbChevronRight,
  TbFolder,
  TbFolderOpen,
  TbGripVertical,
  TbTrash,
  TbMap2,
  TbBooks,
  TbCpu,
  TbBox,
  TbStack2,
  TbCircleDot,
  TbActivity,
  TbServer,
  TbPointFilled,
  TbGitBranch,
  TbArrowRight,
  TbX,
} from 'react-icons/tb'
import { hierarchyApi } from '../../api/hierarchy'
import { listTemplates } from '../../api/workflows'
import { useAppStore } from '../../store'
import type { HierarchyNode, WorkflowTemplate } from '../../types'
import { Button } from '../ui/button'
import { Input } from '../ui/input'

// ── Constants ────────────────────────────────────────────────────────────────

const DIMENSION = 'ZBS'

// ── Palette node definitions ──────────────────────────────────────────────────

interface PaletteItem {
  type: string
  label: string
  icon: React.ReactNode
  color: string
  group: 'structure' | 'class' | 'instance'
}

const PALETTE_ITEMS: PaletteItem[] = [
  // Structure
  { type: 'area',           label: 'Area',           icon: <TbMap2 size={16} />,        color: 'text-amber-500',   group: 'structure' },
  { type: 'library',        label: 'Library',        icon: <TbBooks size={16} />,       color: 'text-purple-500',  group: 'structure' },
  // Classes
  { type: 'cm_class',       label: 'CM Classes',     icon: <TbCircleDot size={16} />,   color: 'text-sky-500',     group: 'class' },
  { type: 'em_class',       label: 'EM Classes',     icon: <TbCpu size={16} />,         color: 'text-blue-500',    group: 'class' },
  { type: 'unit_class',     label: 'Unit Classes',   icon: <TbBox size={16} />,         color: 'text-indigo-500',  group: 'class' },
  { type: 'phase_class',    label: 'Phase Classes',  icon: <TbActivity size={16} />,    color: 'text-violet-500',  group: 'class' },
  // Instances
  { type: 'unit_instance',  label: 'Unit Instance',  icon: <TbStack2 size={16} />,      color: 'text-emerald-500', group: 'instance' },
  { type: 'em_instance',    label: 'EM Instance',    icon: <TbServer size={16} />,      color: 'text-green-500',   group: 'instance' },
  { type: 'cm_instance',    label: 'CM Instance',    icon: <TbPointFilled size={16} />, color: 'text-teal-500',    group: 'instance' },
]

const PALETTE_GROUPS: { key: PaletteItem['group']; label: string }[] = [
  { key: 'structure', label: 'Structure' },
  { key: 'class',     label: 'Classes' },
  { key: 'instance',  label: 'Instances' },
]

function nodeIcon(type: string, open = false, size = 15): React.ReactNode {
  const item = PALETTE_ITEMS.find((p) => p.type === type)
  if (!item) {
    return open
      ? <TbFolderOpen size={size} className="text-amber-500" />
      : <TbFolder size={size} className="text-amber-500" />
  }
  // Folders get open/closed state; others are static
  if (type === 'area' || type === 'library') {
    return open
      ? <TbFolderOpen size={size} className={item.color} />
      : <TbFolder size={size} className={item.color} />
  }
  return <span className={item.color}>{item.icon}</span>
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function flattenNodes(nodes: HierarchyNode[], excludeId?: string): HierarchyNode[] {
  const result: HierarchyNode[] = []
  function visit(n: HierarchyNode) {
    if (n.id !== excludeId) result.push(n)
    n.children.forEach(visit)
  }
  nodes.forEach(visit)
  return result
}

// ── Types ────────────────────────────────────────────────────────────────────

type PendingCreate = { type: string; parentId: string | null } | null

// Condition options for cross-node dependencies
const CONDITION_OPTIONS = [
  { value: 'status_complete',    label: 'Status = Complete',      condition: { target_status: 'complete' } },
  { value: 'status_in_progress', label: 'Status = In Progress',   condition: { target_status: 'in_progress' } },
  { value: 'stage_complete',     label: 'Workflow stage complete', condition: null },  // needs stage_key input
]

// ── Workflow selector dropdown ────────────────────────────────────────────────

function WorkflowSelector({
  nodeId,
  currentTemplateId,
  currentTemplateName,
  templates,
  onSave,
}: {
  nodeId: string
  currentTemplateId: string | null
  currentTemplateName: string | null
  templates: WorkflowTemplate[]
  onSave: (templateId: string | null) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(o => !o) }}
        title={currentTemplateName ? `Workflow: ${currentTemplateName}` : 'Assign workflow'}
        className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-xs transition-colors
          opacity-0 group-hover:opacity-100
          ${currentTemplateId
            ? 'text-primary bg-primary/10 hover:bg-primary/20 opacity-100'
            : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          }`}
      >
        <TbGitBranch size={11} />
        {currentTemplateName
          ? <span className="max-w-[80px] truncate">{currentTemplateName}</span>
          : <span>Workflow</span>
        }
      </button>

      {open && (
        <div
          className="absolute left-0 top-full mt-1 z-50 bg-card border border-border rounded-lg shadow-xl w-52 py-1 overflow-auto max-h-64"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="px-3 py-1.5 text-xs font-medium text-muted-foreground border-b border-border mb-1">
            Assign workflow template
          </p>
          <button
            className="w-full text-left px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent flex items-center gap-2"
            onClick={() => { onSave(null); setOpen(false) }}
          >
            <TbX size={11} /> None
          </button>
          {templates.length === 0 && (
            <p className="px-3 py-2 text-xs text-muted-foreground italic">No templates yet</p>
          )}
          {templates.map(t => (
            <button
              key={t.id}
              className={`w-full text-left px-3 py-1.5 text-xs hover:bg-accent flex items-center gap-2
                ${t.id === currentTemplateId ? 'text-primary font-medium' : 'text-foreground'}`}
              onClick={() => { onSave(t.id); setOpen(false) }}
            >
              <TbGitBranch size={11} className="shrink-0" />
              <span className="truncate">{t.name}</span>
              {t.id === currentTemplateId && <span className="ml-auto text-xs text-primary">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Palette card (right panel) ────────────────────────────────────────────────

function PaletteCard({ item }: { item: PaletteItem }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `palette-${item.type}`,
    data: { source: 'palette', type: item.type },
  })
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`flex items-center gap-2 px-2.5 py-2 rounded-md border border-border bg-card select-none transition-all
        cursor-grab active:cursor-grabbing
        ${isDragging ? 'opacity-30 scale-95' : 'hover:border-primary/40 hover:bg-accent/20'}`}
    >
      <TbGripVertical size={13} className="text-muted-foreground shrink-0" />
      <span className={`shrink-0 ${item.color}`}>{item.icon}</span>
      <span className="text-xs font-medium text-foreground">{item.label}</span>
    </div>
  )
}

// ── Drag ghost ────────────────────────────────────────────────────────────────

function DragGhost({ type }: { type: string }) {
  const item = PALETTE_ITEMS.find((p) => p.type === type)
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-primary bg-card shadow-lg opacity-90 w-44">
      <span className={`shrink-0 ${item?.color ?? ''}`}>{item?.icon}</span>
      <span className="text-sm font-medium">{item?.label ?? type}</span>
    </div>
  )
}

// ── Inline name input ─────────────────────────────────────────────────────────

function PendingInput({
  type,
  onSave,
  onCancel,
}: {
  type: string
  onSave: (name: string) => void
  onCancel: () => void
}) {
  const [v, setV] = useState('')
  const item = PALETTE_ITEMS.find((p) => p.type === type)
  return (
    <form
      className="flex items-center gap-2 py-1"
      onSubmit={(e) => { e.preventDefault(); if (v.trim()) onSave(v.trim()) }}
    >
      <span className={`shrink-0 ${item?.color ?? 'text-muted-foreground'}`}>{item?.icon}</span>
      <Input
        className="h-7 text-sm flex-1"
        value={v}
        onChange={(e) => setV(e.target.value)}
        placeholder={`${item?.label ?? type} name…`}
        autoFocus
        onKeyDown={(e) => e.key === 'Escape' && onCancel()}
      />
      <Button type="submit" size="sm" className="h-7 px-3 text-xs" disabled={!v.trim()}>
        Add
      </Button>
      <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={onCancel}>
        ✕
      </Button>
    </form>
  )
}

// ── Depends-on selector ──────────────────────────────────────────────────────

function DependsOnSelector({
  node,
  allNodes,
  onSave,
}: {
  node: HierarchyNode
  allNodes: HierarchyNode[]
  onSave: (depNodeId: string | null, condition: Record<string, string> | null) => void
}) {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<'node' | 'condition'>('node')
  const [pickedNodeId, setPickedNodeId] = useState<string | null>(null)
  const [conditionType, setConditionType] = useState<string>('status_complete')
  const [stageKey, setStageKey] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  const candidates = flattenNodes(allNodes, node.id)

  useEffect(() => {
    if (!open) return
    function onOut(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false); setStep('node')
      }
    }
    document.addEventListener('mousedown', onOut)
    return () => document.removeEventListener('mousedown', onOut)
  }, [open])

  function buildCondition(): Record<string, string> | null {
    if (conditionType === 'stage_complete') {
      if (!stageKey.trim()) return null
      return { target_stage_key: stageKey.trim(), operator: 'complete' }
    }
    return CONDITION_OPTIONS.find(o => o.value === conditionType)?.condition ?? null
  }

  function handleSave() {
    const cond = buildCondition()
    if (!pickedNodeId || !cond) return
    onSave(pickedNodeId, cond)
    setOpen(false); setStep('node')
  }

  const conditionLabel = () => {
    if (!node.dependency_condition) return null
    if (node.dependency_condition.target_status) return `status = ${node.dependency_condition.target_status}`
    if (node.dependency_condition.target_stage_key) return `stage "${node.dependency_condition.target_stage_key}" complete`
    return 'condition set'
  }
  const label = conditionLabel()

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(o => !o); setStep('node') }}
        title={node.depends_on_node_name ? `Depends on: ${node.depends_on_node_name}` : 'Set dependency'}
        className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-xs transition-colors
          opacity-0 group-hover:opacity-100
          ${node.depends_on_node_id
            ? 'text-violet-600 bg-violet-50 dark:bg-violet-900/20 opacity-100 hover:bg-violet-100 dark:hover:bg-violet-900/40'
            : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          }`}
      >
        <TbArrowRight size={11} />
        {node.depends_on_node_name
          ? <span className="max-w-[80px] truncate">{node.depends_on_node_name}</span>
          : <span>Depends on</span>
        }
        {label && <span className="opacity-60">({label})</span>}
      </button>

      {open && (
        <div
          className="absolute left-0 top-full mt-1 z-50 bg-card border border-border rounded-lg shadow-xl w-64 overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {step === 'node' && (
            <>
              <p className="px-3 py-2 text-xs font-medium text-muted-foreground border-b border-border">
                Objects here depend on objects in…
              </p>
              <div className="overflow-auto max-h-52 py-1">
                <button
                  className="w-full text-left px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent flex items-center gap-2"
                  onClick={() => { onSave(null, null); setOpen(false) }}
                >
                  <TbX size={11} /> No dependency
                </button>
                {candidates.map(n => (
                  <button
                    key={n.id}
                    className={`w-full text-left px-3 py-1.5 text-xs hover:bg-accent flex items-center gap-2
                      ${n.id === node.depends_on_node_id ? 'text-violet-600 font-medium' : 'text-foreground'}`}
                    onClick={() => { setPickedNodeId(n.id); setStep('condition') }}
                  >
                    <TbArrowRight size={11} className="shrink-0" />
                    <span className="truncate">{n.name}</span>
                  </button>
                ))}
              </div>
            </>
          )}

          {step === 'condition' && (
            <div className="p-3 space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Required condition</p>
              <select
                className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                value={conditionType}
                onChange={e => setConditionType(e.target.value)}
              >
                {CONDITION_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              {conditionType === 'stage_complete' && (
                <input
                  className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                  placeholder="Stage key e.g. engineering"
                  value={stageKey}
                  onChange={e => setStageKey(e.target.value)}
                />
              )}
              <div className="flex gap-2 pt-1">
                <button onClick={() => setStep('node')} className="text-xs text-muted-foreground hover:text-foreground">← Back</button>
                <button
                  onClick={handleSave}
                  disabled={conditionType === 'stage_complete' && !stageKey.trim()}
                  className="ml-auto text-xs px-3 py-1 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-40"
                >
                  Save
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Recursive tree node ───────────────────────────────────────────────────────

function TreeNode({
  node,
  depth,
  pending,
  expanded,
  draggingType,
  templates,
  allNodes,
  onToggle,
  onDelete,
  onSetWorkflow,
  onSetDependency,
  onPendingSave,
  onPendingCancel,
}: {
  node: HierarchyNode
  depth: number
  pending: PendingCreate
  expanded: Set<string>
  draggingType: string | null
  templates: WorkflowTemplate[]
  allNodes: HierarchyNode[]
  onToggle: (id: string) => void
  onDelete: (id: string) => void
  onSetWorkflow: (nodeId: string, templateId: string | null) => void
  onSetDependency: (nodeId: string, depNodeId: string | null, condition: Record<string, string> | null) => void
  onPendingSave: (name: string) => void
  onPendingCancel: () => void
}) {
  const { setNodeRef, isOver } = useDroppable({ id: `node-${node.id}` })
  const isExpanded = expanded.has(node.id)
  const hasPendingChild = pending?.parentId === node.id
  const hasChildren = node.children.length > 0 || hasPendingChild

  return (
    <div ref={setNodeRef} className="select-none">
      {/* Node header */}
      <div
        className={`flex items-center gap-1.5 px-2 py-1.5 rounded-md cursor-pointer transition-colors group
          ${isOver && draggingType
            ? 'bg-primary/10 ring-1 ring-primary/40'
            : 'hover:bg-accent/40'
          }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => onToggle(node.id)}
      >
        {/* Expand/collapse */}
        <span className="w-3.5 shrink-0 text-muted-foreground">
          {hasChildren || hasPendingChild
            ? isExpanded
              ? <TbChevronDown size={12} />
              : <TbChevronRight size={12} />
            : <span className="w-3" />
          }
        </span>

        {/* Icon */}
        <span className="shrink-0">{nodeIcon(node.description ?? '', isExpanded)}</span>

        <span className="text-sm text-foreground flex-1 truncate">{node.name}</span>

        {/* Drop hint badge */}
        {isOver && draggingType && (
          <span className="text-xs text-primary font-medium shrink-0 mr-1">↓ drop here</span>
        )}

        {/* Workflow selector */}
        <WorkflowSelector
          nodeId={node.id}
          currentTemplateId={node.workflow_template_id}
          currentTemplateName={node.workflow_template_name}
          templates={templates}
          onSave={(templateId) => onSetWorkflow(node.id, templateId)}
        />

        {/* Depends-on selector */}
        <DependsOnSelector
          node={node}
          allNodes={allNodes}
          onSave={(depNodeId, condition) => onSetDependency(node.id, depNodeId, condition)}
        />

        {/* Delete */}
        <button
          className="p-0.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive
            opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
          onClick={(e) => { e.stopPropagation(); onDelete(node.id) }}
          title="Delete"
        >
          <TbTrash size={12} />
        </button>
      </div>

      {/* Children */}
      {isExpanded && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              pending={pending}
              expanded={expanded}
              draggingType={draggingType}
              templates={templates}
              allNodes={allNodes}
              onToggle={onToggle}
              onDelete={onDelete}
              onSetWorkflow={onSetWorkflow}
              onSetDependency={onSetDependency}
              onPendingSave={onPendingSave}
              onPendingCancel={onPendingCancel}
            />
          ))}

          {hasPendingChild && (
            <div style={{ paddingLeft: `${(depth + 1) * 16 + 8}px` }} className="py-1 pr-2">
              <PendingInput
                type={pending!.type}
                onSave={onPendingSave}
                onCancel={onPendingCancel}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Root drop zone ────────────────────────────────────────────────────────────

function RootDropZone({
  children,
  isEmpty,
}: {
  children: React.ReactNode
  isEmpty: boolean
}) {
  const { setNodeRef, isOver } = useDroppable({ id: 'root' })
  return (
    <div
      ref={setNodeRef}
      className={`flex-1 rounded-xl border-2 border-dashed transition-colors min-h-[280px] ${
        isOver ? 'border-primary bg-primary/5' : 'border-border'
      }`}
    >
      {isEmpty ? (
        <div className="flex flex-col items-center justify-center h-full min-h-[220px] gap-2 text-center px-4">
          {isOver
            ? <p className="text-sm text-primary font-medium">↓ Release to create here</p>
            : <>
                <TbFolder size={36} className="text-muted-foreground/20" />
                <p className="text-sm text-muted-foreground">
                  Drag a <strong>Folder</strong> or <strong>Unit</strong> from the palette to start building your structure
                </p>
              </>
          }
        </div>
      ) : (
        <div className="p-2 space-y-0.5">
          {children}
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function HierarchyBuilder() {
  const { selectedProjectId } = useAppStore()
  const qc = useQueryClient()

  const { data: nodes = [] } = useQuery({
    queryKey: ['hierarchy-nodes', selectedProjectId, DIMENSION],
    queryFn: () => hierarchyApi.listNodes(selectedProjectId!, DIMENSION),
    enabled: !!selectedProjectId,
  })

  const { data: templates = [] } = useQuery({
    queryKey: ['workflow-templates'],
    queryFn: listTemplates,
  })

  const createNode = useMutation({
    mutationFn: hierarchyApi.createNode,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hierarchy-nodes', selectedProjectId, DIMENSION] }),
  })

  const updateNode = useMutation({
    mutationFn: ({ id, ...body }: { id: string; workflow_template_id: string | null }) =>
      hierarchyApi.updateNode(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hierarchy-nodes', selectedProjectId, DIMENSION] }),
  })

  const deleteNode = useMutation({
    mutationFn: hierarchyApi.deleteNode,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hierarchy-nodes', selectedProjectId, DIMENSION] }),
  })

  const handleSetWorkflow = (nodeId: string, templateId: string | null) => {
    updateNode.mutate({ id: nodeId, workflow_template_id: templateId })
  }

  const handleSetDependency = (nodeId: string, depNodeId: string | null, condition: Record<string, string> | null) => {
    updateNode.mutate({ id: nodeId, depends_on_node_id: depNodeId, dependency_condition: condition })
  }

  const [pending, setPending] = useState<PendingCreate>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [draggingType, setDraggingType] = useState<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  )

  const toggleExpanded = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const forceExpand = (id: string) =>
    setExpanded((prev) => new Set([...prev, id]))

  function handleDragStart(e: DragStartEvent) {
    setDraggingType((e.active.data.current?.type as string) ?? null)
  }

  function handleDragEnd(e: DragEndEvent) {
    setDraggingType(null)
    const { active, over } = e
    if (!over || active.data.current?.source !== 'palette') return

    const type = active.data.current.type as string

    if (over.id === 'root') {
      setPending({ type, parentId: null })
    } else if (typeof over.id === 'string' && over.id.startsWith('node-')) {
      const parentId = over.id.replace('node-', '')
      forceExpand(parentId)
      setPending({ type, parentId })
    }
  }

  function handlePendingSave(name: string) {
    if (!pending || !selectedProjectId) return
    createNode.mutate({
      project_id: selectedProjectId,
      dimension: DIMENSION,
      name,
      description: pending.type,
      parent_id: pending.parentId,
      position: 0,
    })
    setPending(null)
  }

  if (!selectedProjectId) {
    return (
      <div className="text-sm text-muted-foreground py-10 text-center">
        Select a project to manage its structure.
      </div>
    )
  }

  const isEmpty = nodes.length === 0 && pending?.parentId !== null

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="flex gap-4 h-full min-h-[400px]">

        {/* ── Left: tree ───────────────────────────────────────────────── */}
        <div className="flex flex-col flex-1 min-w-0 gap-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">Project Structure</h2>
            <span className="text-xs text-muted-foreground px-1.5 py-0.5 bg-muted rounded font-mono">
              ZBS
            </span>
          </div>

          <RootDropZone isEmpty={isEmpty}>
            {nodes.map((node) => (
              <TreeNode
                key={node.id}
                node={node}
                depth={0}
                pending={pending}
                expanded={expanded}
                draggingType={draggingType}
                templates={templates}
                allNodes={nodes}
                onToggle={toggleExpanded}
                onDelete={(id) => deleteNode.mutate(id)}
                onSetWorkflow={handleSetWorkflow}
                onSetDependency={handleSetDependency}
                onPendingSave={handlePendingSave}
                onPendingCancel={() => setPending(null)}
              />
            ))}

            {/* Root-level pending input */}
            {pending?.parentId === null && (
              <div className="px-2 py-1">
                <PendingInput
                  type={pending.type}
                  onSave={handlePendingSave}
                  onCancel={() => setPending(null)}
                />
              </div>
            )}
          </RootDropZone>
        </div>

        {/* ── Right: palette ───────────────────────────────────────────── */}
        <div className="w-48 shrink-0 flex flex-col gap-3 overflow-y-auto">
          <h2 className="text-sm font-semibold text-foreground">Palette</h2>

          {PALETTE_GROUPS.map((group) => (
            <div key={group.key}>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5">
                {group.label}
              </p>
              <div className="space-y-1">
                {PALETTE_ITEMS.filter((p) => p.group === group.key).map((item) => (
                  <PaletteCard key={item.type} item={item} />
                ))}
              </div>
            </div>
          ))}

          <div className="rounded-lg bg-muted/40 border border-border px-3 py-2.5 text-xs text-muted-foreground space-y-1 mt-1">
            <p>Drag any item onto the tree — drop at root for top-level, drop onto a node to nest inside it.</p>
          </div>
        </div>
      </div>

      <DragOverlay dropAnimation={null}>
        {draggingType ? <DragGhost type={draggingType} /> : null}
      </DragOverlay>
    </DndContext>
  )
}
