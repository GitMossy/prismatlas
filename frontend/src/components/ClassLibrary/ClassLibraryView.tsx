import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import { useClassDefinitions, useDeleteClassDefinition } from '../../hooks/useClassDefinitions'
import { listTemplates } from '../../api/workflows'
import type { ClassDefinition, WorkflowTemplate } from '../../types'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import ClassFormModal from './ClassFormModal'

// Derive type filter tabs dynamically from loaded classes (V3: free-text object_type)

function StatusBadge({ cls, templates }: { cls: ClassDefinition; templates: WorkflowTemplate[] }) {
  if (!cls.workflow_template_id) {
    return <Badge variant="destructive" className="text-xs">No template</Badge>
  }
  const tpl = templates.find((t) => t.id === cls.workflow_template_id)
  return <Badge variant="secondary" className="text-xs">{tpl?.name ?? 'Template linked'}</Badge>
}

interface RowProps {
  cls: ClassDefinition
  templates: WorkflowTemplate[]
  onEdit: (cls: ClassDefinition) => void
  onDeleted: (id: string) => void
}

function ClassRow({ cls, templates, onEdit, onDeleted }: RowProps) {
  const [confirming, setConfirming] = useState(false)
  const deleteMutation = useDeleteClassDefinition()

  const handleDelete = () => {
    deleteMutation.mutate(cls.id, { onSuccess: () => onDeleted(cls.id) })
  }

  return (
    <tr className="border-b border-border hover:bg-muted/30 transition-colors">
      <td className="px-4 py-2.5 text-sm font-medium text-foreground">{cls.name}</td>
      <td className="px-4 py-2.5 text-xs text-muted-foreground">{cls.object_type}</td>
      <td className="px-4 py-2.5 text-xs text-muted-foreground">{cls.instance_count}</td>
      <td className="px-4 py-2.5 text-xs text-muted-foreground">{cls.complexity}×</td>
      <td className="px-4 py-2.5">
        <StatusBadge cls={cls} templates={templates} />
      </td>
      <td className="px-4 py-2.5 text-xs text-muted-foreground max-w-[200px] truncate">
        {cls.description || '—'}
      </td>
      <td className="px-4 py-2.5 text-right whitespace-nowrap">
        {confirming ? (
          <span className="flex items-center justify-end gap-2">
            <span className="text-xs text-muted-foreground">Delete?</span>
            <button
              className="text-xs text-destructive hover:underline"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting…' : 'Yes'}
            </button>
            <button className="text-xs text-muted-foreground hover:underline" onClick={() => setConfirming(false)}>
              No
            </button>
          </span>
        ) : (
          <span className="flex items-center justify-end gap-3">
            <button className="text-xs text-primary hover:underline" onClick={() => onEdit(cls)}>Edit</button>
            <button className="text-xs text-destructive hover:underline" onClick={() => setConfirming(true)}>Delete</button>
          </span>
        )}
      </td>
    </tr>
  )
}

export default function ClassLibraryView() {
  const { selectedProjectId } = useAppStore()
  const queryClient = useQueryClient()

  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<ClassDefinition | null>(null)

  const { data: allClasses = [], isLoading } = useClassDefinitions(selectedProjectId)
  const { data: templates = [] } = useQuery<WorkflowTemplate[]>({
    queryKey: ['workflow-templates'],
    queryFn: listTemplates,
  })

  // Unique types present in the project — derived dynamically (free-text V3)
  const presentTypes = [...new Set(allClasses.map((c) => c.object_type))].sort()

  const filtered = typeFilter === 'all'
    ? allClasses
    : allClasses.filter((c) => c.object_type === typeFilter)

  const configuredCount = allClasses.filter((c) => !!c.workflow_template_id).length

  if (!selectedProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        Select a project to view its class library.
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Class Library</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {allClasses.length} class{allClasses.length !== 1 ? 'es' : ''} — {configuredCount} configured
          </p>
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)}>+ New Class</Button>
      </div>

      {/* Type filter tabs — dynamically derived from loaded classes */}
      <div className="flex gap-1 mb-4 flex-wrap">
        {['all', ...presentTypes].map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              typeFilter === t
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-accent hover:text-foreground'
            }`}
          >
            {t === 'all' ? 'All' : t}
            {t !== 'all' && (
              <span className="ml-1.5 opacity-60">
                {allClasses.filter((c) => c.object_type === t).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-sm text-muted-foreground">
          No class definitions{typeFilter !== 'all' ? ` for type "${typeFilter}"` : ''}.{' '}
          <button className="text-primary hover:underline" onClick={() => setShowCreate(true)}>
            Create one.
          </button>
        </div>
      ) : (
        <div className="rounded-md border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Name</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Type</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Count</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Complexity</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Template</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Description</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((cls) => (
                <ClassRow
                  key={cls.id}
                  cls={cls}
                  templates={templates}
                  onEdit={setEditTarget}
                  onDeleted={() => queryClient.invalidateQueries({ queryKey: ['class-definitions'] })}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && selectedProjectId && (
        <ClassFormModal
          mode="create"
          projectId={selectedProjectId}
          onClose={() => setShowCreate(false)}
          onSuccess={() => setShowCreate(false)}
        />
      )}

      {editTarget && selectedProjectId && (
        <ClassFormModal
          mode="edit"
          projectId={selectedProjectId}
          initialValues={editTarget}
          onClose={() => setEditTarget(null)}
          onSuccess={() => setEditTarget(null)}
        />
      )}
    </div>
  )
}
