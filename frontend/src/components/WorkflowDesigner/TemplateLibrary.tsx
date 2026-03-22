import { useState } from 'react'
import {
  useTemplates,
  useTemplateVersions,
  useDeleteTemplate,
  useDeleteTemplateVersion,
  useActivateTemplateVersion,
} from '../../hooks/useWorkflows'
import type { WorkflowTemplate, WorkflowTemplateVersion } from '../../types'

interface Props {
  selectedTemplateId: string | null
  selectedVersionId: string | null
  onSelectTemplate: (templateId: string) => void
  onSelectVersion: (versionId: string) => void
  onCreateTemplate: () => void
  onEditTemplate: (template: WorkflowTemplate) => void
  onDeletedTemplate: (templateId: string) => void
  onVersionDeleted: (templateId: string, versionId: string) => void
}

function VersionRow({
  version,
  templateId,
  isSelected,
  onSelect,
  onDeleted,
}: {
  version: WorkflowTemplateVersion
  templateId: string
  isSelected: boolean
  onSelect: () => void
  onDeleted: (versionId: string) => void
}) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const { mutate: deleteVersion, isPending: deleting } = useDeleteTemplateVersion(templateId)
  const { mutate: activate, isPending: activating } = useActivateTemplateVersion(templateId)

  const handleDelete = () => {
    deleteVersion(version.version_number, {
      onSuccess: () => onDeleted(version.id),
      onError: (err: unknown) => {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        alert(msg ?? 'Failed to delete version')
        setConfirmDelete(false)
      },
    })
  }

  return (
    <div className={`group flex items-center gap-1 rounded px-2 py-1.5 text-xs ${
      isSelected ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent'
    }`}>
      <button onClick={onSelect} className="flex-1 text-left">
        v{version.version_number}
        {version.is_active && (
          <span className={`ml-1.5 text-xs ${isSelected ? 'opacity-70' : 'text-primary font-medium'}`}>
            (active)
          </span>
        )}
      </button>

      {!confirmDelete ? (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!version.is_active && (
            <button
              onClick={() => activate(version.version_number)}
              disabled={activating}
              title="Set as active"
              className={`px-1 rounded hover:bg-primary/10 hover:text-primary ${isSelected ? 'text-primary-foreground/60 hover:bg-primary/80 hover:text-white' : 'text-muted-foreground'}`}
            >
              ✓
            </button>
          )}
          <button
            onClick={() => setConfirmDelete(true)}
            title="Delete version"
            className={`px-1 rounded hover:bg-red-100 hover:text-red-600 ${isSelected ? 'text-primary-foreground/60 hover:bg-primary/80 hover:text-white' : 'text-muted-foreground'}`}
          >
            ×
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-1">
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="px-1.5 py-0.5 rounded bg-red-500 text-white text-xs hover:bg-red-600"
          >
            {deleting ? '…' : 'Del'}
          </button>
          <button
            onClick={() => setConfirmDelete(false)}
            className="px-1.5 py-0.5 rounded bg-gray-200 text-gray-600 text-xs hover:bg-gray-300"
          >
            No
          </button>
        </div>
      )}
    </div>
  )
}

function TemplateItem({
  template,
  isSelected,
  onSelect,
  onSelectVersion,
  onEdit,
  onDeleted,
  onVersionDeleted,
  selectedVersionId,
}: {
  template: WorkflowTemplate
  isSelected: boolean
  onSelect: () => void
  onSelectVersion: (versionId: string) => void
  onEdit: () => void
  onDeleted: () => void
  onVersionDeleted: (versionId: string) => void
  selectedVersionId: string | null
}) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const { data: versions = [] } = useTemplateVersions(isSelected ? template.id : null)
  const { mutate: deleteTemplate, isPending: deleting } = useDeleteTemplate()

  const handleDelete = () => {
    deleteTemplate(template.id, {
      onSuccess: onDeleted,
      onError: (err: unknown) => {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        alert(msg ?? 'Failed to delete template')
        setConfirmDelete(false)
      },
    })
  }

  return (
    <div>
      <div className={`group flex items-center gap-1 rounded border transition-colors ${
        isSelected ? 'bg-primary/5 border-primary/20' : 'border-transparent hover:bg-accent/40'
      }`}>
        <button onClick={onSelect} className="flex-1 text-left px-3 py-2.5">
          <p className="font-medium text-foreground text-sm truncate">{template.name}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{template.applies_to_type}</p>
        </button>

        {!confirmDelete ? (
          <div className="flex items-center gap-0.5 pr-2 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
            <button
              onClick={(e) => { e.stopPropagation(); onEdit() }}
              title="Edit template"
              className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent text-xs"
            >
              ✎
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); setConfirmDelete(true) }}
              title="Delete template"
              className="p-1 rounded text-muted-foreground hover:text-red-600 hover:bg-red-50 text-xs"
            >
              ×
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1 pr-2 shrink-0">
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="px-1.5 py-0.5 rounded bg-red-500 text-white text-xs hover:bg-red-600"
            >
              {deleting ? '…' : 'Del'}
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="px-1.5 py-0.5 rounded bg-gray-200 text-gray-600 text-xs hover:bg-gray-300"
            >
              No
            </button>
          </div>
        )}
      </div>

      {isSelected && versions.length > 0 && (
        <div className="ml-3 mt-1 mb-2 space-y-0.5">
          {versions.map((v) => (
            <VersionRow
              key={v.id}
              version={v}
              templateId={template.id}
              isSelected={selectedVersionId === v.id}
              onSelect={() => onSelectVersion(v.id)}
              onDeleted={onVersionDeleted}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function TemplateLibrary({
  selectedTemplateId,
  selectedVersionId,
  onSelectTemplate,
  onSelectVersion,
  onCreateTemplate,
  onEditTemplate,
  onDeletedTemplate,
  onVersionDeleted,
}: Props) {
  const { data: templates = [], isLoading } = useTemplates()
  const [filter, setFilter] = useState('')

  const filtered = templates.filter(
    (t) =>
      t.name.toLowerCase().includes(filter.toLowerCase()) ||
      t.applies_to_type.toLowerCase().includes(filter.toLowerCase()),
  )

  return (
    <aside className="w-60 border-r border-border flex flex-col h-full bg-card shrink-0">
      <div className="px-3 py-3 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Templates</span>
          <button
            onClick={onCreateTemplate}
            className="text-xs text-primary hover:text-primary/80 font-medium"
          >
            + New
          </button>
        </div>
        <input
          className="w-full border border-border bg-background rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          placeholder="Filter…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="flex-1 overflow-auto p-2 space-y-1">
        {isLoading && <p className="text-xs text-muted-foreground px-2 py-2">Loading…</p>}
        {!isLoading && filtered.length === 0 && (
          <p className="text-xs text-muted-foreground px-2 py-4 text-center">No templates yet</p>
        )}
        {filtered.map((t) => (
          <TemplateItem
            key={t.id}
            template={t}
            isSelected={selectedTemplateId === t.id}
            onSelect={() => onSelectTemplate(t.id)}
            onSelectVersion={onSelectVersion}
            onEdit={() => onEditTemplate(t)}
            onDeleted={() => onDeletedTemplate(t.id)}
            onVersionDeleted={(versionId) => onVersionDeleted(t.id, versionId)}
            selectedVersionId={selectedVersionId}
          />
        ))}
      </div>
    </aside>
  )
}
