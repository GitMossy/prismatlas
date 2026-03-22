import { useProject, useAreas, useUnits } from '../../hooks/useProjects'
import { useAppStore } from '../../store'
import { useThemeStore } from '../../store/theme'
import { Sun, Moon } from 'lucide-react'

const VIEW_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  graph: 'Graph View',
  list: 'List View',
  cube: 'Cube View',
}

export default function TopBar() {
  const { selectedProjectId, viewMode, hierarchyContext, clearHierarchyContext, setHierarchyArea } = useAppStore()
  const { data: project } = useProject(selectedProjectId)
  const { data: areas = [] } = useAreas(hierarchyContext.areaId ? selectedProjectId : null)
  const { data: units = [] } = useUnits(hierarchyContext.unitId ? hierarchyContext.areaId : null)
  const { theme, toggleTheme } = useThemeStore()

  const area = areas.find((a) => a.id === hierarchyContext.areaId)
  const unit = units.find((u) => u.id === hierarchyContext.unitId)

  return (
    <header className="h-12 bg-background border-b border-border flex items-center px-6 shrink-0">
      <span className="text-muted-foreground text-sm">{VIEW_LABELS[viewMode] ?? viewMode}</span>
      {project && (
        <>
          <span className="mx-2 text-muted-foreground/40">/</span>
          {hierarchyContext.areaId ? (
            <button
              className="text-muted-foreground text-sm hover:text-primary transition-colors"
              onClick={() => clearHierarchyContext()}
            >
              {project.name}
            </button>
          ) : (
            <span className="text-foreground text-sm font-medium">{project.name}</span>
          )}
        </>
      )}
      {area && (
        <>
          <span className="mx-2 text-muted-foreground/40">/</span>
          {hierarchyContext.unitId ? (
            <button
              className="text-muted-foreground text-sm hover:text-primary transition-colors truncate max-w-[160px]"
              title={area.name}
              onClick={() => setHierarchyArea(area.id)}
            >
              {area.name}
            </button>
          ) : (
            <span className="text-foreground text-sm font-medium truncate max-w-[160px]" title={area.name}>
              {area.name}
            </span>
          )}
        </>
      )}
      {unit && (
        <>
          <span className="mx-2 text-muted-foreground/40">/</span>
          <span className="text-foreground text-sm font-medium truncate max-w-[160px]" title={unit.name}>
            {unit.name}
          </span>
        </>
      )}

      {/* Dark mode toggle */}
      <div className="ml-auto">
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  )
}
