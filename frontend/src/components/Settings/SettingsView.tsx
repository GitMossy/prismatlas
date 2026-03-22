/**
 * Settings / Configuration View
 *
 * Tabs:
 *   Projects   — create, rename, delete projects
 *   Structure  — manage Areas and Units within the selected project
 *   Object Types — view/manage the free-text object types in use
 *   Calendars  — work calendars for calendar-aware CPM (FR-4.4.2)
 *
 * Accessible via the Settings nav item (bottom of sidebar).
 */
import { useState } from 'react'
import { TbPlus, TbPencil, TbTrash } from 'react-icons/tb'
import { useProjects, useDeleteProject } from '../../hooks/useProjects'
import HierarchyBuilder from './HierarchyBuilder'
import WorkflowDesigner from '../WorkflowDesigner/WorkflowDesigner'
import { useAppStore } from '../../store'
import type { Project } from '../../types'
import { Button } from '../ui/button'
import ProjectFormModal from './ProjectFormModal'

type Tab = 'projects' | 'structure' | 'workflows' | 'calendars'

// ── Projects tab ─────────────────────────────────────────────────────────────

function ProjectsTab() {
  const { data: projects = [] } = useProjects()
  const deleteProject = useDeleteProject()
  const { selectedProjectId, setSelectedProject } = useAppStore()
  const [modal, setModal] = useState<'create' | { edit: Project } | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<Project | null>(null)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">Projects</h2>
        <Button size="sm" className="h-7 text-xs gap-1" onClick={() => setModal('create')}>
          <TbPlus size={13} /> New Project
        </Button>
      </div>

      <div className="rounded-md border border-border overflow-hidden">
        {projects.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-muted-foreground">
            No projects yet. Create one to get started.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 border-b border-border text-xs text-muted-foreground">
                <th className="text-left px-4 py-2 font-medium">Name</th>
                <th className="text-left px-4 py-2 font-medium hidden sm:table-cell">Description</th>
                <th className="px-4 py-2 w-20"></th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr
                  key={p.id}
                  className={`border-b border-border last:border-0 ${
                    p.id === selectedProjectId ? 'bg-primary/5' : 'hover:bg-accent/30'
                  }`}
                >
                  <td className="px-4 py-2.5 font-medium text-foreground">
                    <button
                      className="hover:text-primary transition-colors text-left"
                      onClick={() => setSelectedProject(p.id)}
                    >
                      {p.name}
                    </button>
                    {p.id === selectedProjectId && (
                      <span className="ml-2 text-xs text-primary font-normal">(active)</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground hidden sm:table-cell">
                    {p.description ?? <span className="italic">—</span>}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-1 justify-end">
                      <button
                        className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
                        title="Edit"
                        onClick={() => setModal({ edit: p })}
                      >
                        <TbPencil size={14} />
                      </button>
                      <button
                        className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                        title="Delete"
                        onClick={() => setConfirmDelete(p)}
                      >
                        <TbTrash size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Delete confirmation */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-card border border-border rounded-lg shadow-xl p-5 max-w-sm w-full mx-4 space-y-3">
            <p className="text-sm font-semibold text-foreground">Delete "{confirmDelete.name}"?</p>
            <p className="text-xs text-muted-foreground">
              This permanently deletes the project and all its objects, documents, and workflows. This cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setConfirmDelete(null)}>Cancel</Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  deleteProject.mutate(confirmDelete.id, {
                    onSuccess: () => {
                      if (selectedProjectId === confirmDelete.id) setSelectedProject(null)
                      setConfirmDelete(null)
                    },
                  })
                }}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}

      {modal === 'create' && (
        <ProjectFormModal mode="create" onClose={() => setModal(null)} />
      )}
      {modal && typeof modal === 'object' && 'edit' in modal && (
        <ProjectFormModal mode="edit" initial={modal.edit} onClose={() => setModal(null)} />
      )}
    </div>
  )
}

// ── Structure tab ─────────────────────────────────────────────────────────────

function StructureTab() {
  return <HierarchyBuilder />
}

// ── Workflow Designer tab ──────────────────────────────────────────────────────

function WorkflowsTab() {
  return <WorkflowDesigner />
}

// ── Calendars tab (stub — full management deferred) ──────────────────────────

function CalendarsTab() {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold">Work Calendars</h2>
      <p className="text-sm text-muted-foreground">
        Work calendars define which days count as working days and carry public-holiday exceptions.
        They are used by the CPM engine to compute calendar-aware schedule dates.
      </p>
      <div className="rounded-md border border-border px-4 py-6 text-center text-sm text-muted-foreground">
        Calendar management UI coming soon. Calendars can be managed via the API at{' '}
        <code className="text-xs bg-muted px-1 py-0.5 rounded">/calendars</code>.
      </div>
    </div>
  )
}

// ── Main SettingsView ─────────────────────────────────────────────────────────

const TABS: { key: Tab; label: string }[] = [
  { key: 'projects',   label: 'Projects' },
  { key: 'structure',  label: 'Project Structure' },
  { key: 'workflows',  label: 'Workflow Designer' },
  { key: 'calendars',  label: 'Calendars' },
]

export default function SettingsView() {
  const [tab, setTab] = useState<Tab>('projects')

  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-background">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border shrink-0 bg-card">
        <h1 className="text-base font-semibold text-foreground">Configuration</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Manage projects, hierarchy structure, and system settings.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-0 px-6 border-b border-border shrink-0 bg-card">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`pb-2 pt-3 px-3 text-sm border-b-2 transition-colors ${
              tab === t.key
                ? 'border-primary text-primary font-medium'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === 'workflows' ? (
        <div className="flex flex-1 overflow-hidden">
          <WorkflowsTab />
        </div>
      ) : (
        <div className="flex-1 overflow-auto px-6 py-5">
          {tab === 'projects'  && <ProjectsTab />}
          {tab === 'structure' && <StructureTab />}
          {tab === 'calendars' && <CalendarsTab />}
        </div>
      )}
    </div>
  )
}
