import { useState } from 'react'
import { useProjects } from '../../hooks/useProjects'
import { useAppStore } from '../../store'
import type { ViewMode } from '../../types'
import HierarchyTree from './HierarchyTree'
import ProjectFormModal from '../Settings/ProjectFormModal'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import {
  TbLayoutDashboard,
  TbHierarchy2,
  TbList,
  TbTimeline,
  TbLayoutGrid,
  TbBox,
  TbLibrary,
  TbSettings,
  TbPlus,
} from 'react-icons/tb'
import type { IconType } from 'react-icons'

const NAV_ITEMS: { label: string; mode: ViewMode; requiresProject: boolean; Icon: IconType }[] = [
  { label: 'Dashboard',         mode: 'dashboard', requiresProject: true,  Icon: TbLayoutDashboard },
  { label: 'Graph View',        mode: 'graph',     requiresProject: true,  Icon: TbHierarchy2 },
  { label: 'List View',         mode: 'list',      requiresProject: true,  Icon: TbList },
  { label: 'Gantt View',        mode: 'gantt',     requiresProject: true,  Icon: TbTimeline },
  { label: 'Matrix View',       mode: 'matrix',    requiresProject: true,  Icon: TbLayoutGrid },
  { label: 'Cube View',         mode: 'cube',      requiresProject: true,  Icon: TbBox },
  { label: 'Class Library',    mode: 'library',   requiresProject: true,  Icon: TbLibrary },
]

export default function Sidebar() {
  const { data: projects = [] } = useProjects()
  const { selectedProjectId, viewMode, setSelectedProject, setViewMode } = useAppStore()
  const [showNewProject, setShowNewProject] = useState(false)

  return (
    <aside className="w-56 bg-card text-card-foreground flex flex-col h-full shrink-0 border-r border-border">
      <div className="px-4 py-5 border-b border-border">
        <span className="text-lg font-semibold tracking-wide">
          Prism<span className="text-primary">Atlas</span>
        </span>
        <p className="text-xs text-muted-foreground mt-0.5">Project Navigator</p>
      </div>

      {/* Project selector */}
      <div className="px-4 py-4 border-b border-border space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs uppercase text-muted-foreground tracking-wider">Project</p>
          <button
            title="New project"
            onClick={() => setShowNewProject(true)}
            className="p-0.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
          >
            <TbPlus size={14} />
          </button>
        </div>
        <Select value={selectedProjectId ?? ''} onValueChange={(v) => setSelectedProject(v || null)}>
          <SelectTrigger className="w-full text-sm h-8">
            <SelectValue placeholder="— select project —" />
          </SelectTrigger>
          <SelectContent>
            {projects.map((p) => (
              <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
            ))}
            {projects.length === 0 && (
              <div className="px-2 py-3 text-xs text-muted-foreground text-center">
                No projects. Click + to create one.
              </div>
            )}
          </SelectContent>
        </Select>
      </div>

      {/* Navigation */}
      <nav className="px-2 py-4 space-y-0.5 border-b border-border">
        {NAV_ITEMS.map(({ label, mode, requiresProject, Icon }) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            disabled={requiresProject && !selectedProjectId}
            className={`w-full text-left px-3 py-2 rounded text-sm transition-colors flex items-center gap-2.5
              ${viewMode === mode
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-40 disabled:cursor-not-allowed'
              }`}
          >
            <Icon className="shrink-0" size={16} />
            {label}
          </button>
        ))}
      </nav>

      {/* Hierarchy tree */}
      {selectedProjectId && (
        <div className="flex-1 overflow-y-auto">
          <HierarchyTree />
        </div>
      )}

      {/* Settings — pinned to bottom */}
      <div className="px-2 py-3 border-t border-border shrink-0">
        <button
          onClick={() => setViewMode('settings')}
          className={`w-full text-left px-3 py-2 rounded text-sm transition-colors flex items-center gap-2.5
            ${viewMode === 'settings'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-foreground'
            }`}
        >
          <TbSettings className="shrink-0" size={16} />
          Settings
        </button>
      </div>

      {showNewProject && (
        <ProjectFormModal
          mode="create"
          onClose={() => setShowNewProject(false)}
          onSuccess={(p) => setSelectedProject(p.id)}
        />
      )}
    </aside>
  )
}
