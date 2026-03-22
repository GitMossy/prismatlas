import { useEffect } from 'react'
import { useAppStore } from './store'
import { useHistoryStore } from './store/history'
import Sidebar from './components/Layout/Sidebar'
import TopBar from './components/Layout/TopBar'
import Dashboard from './components/Dashboard/Dashboard'
import GraphView from './components/GraphView/GraphView'
import ListView from './components/ListView/ListView'
import DetailPanel from './components/DetailPanel/DetailPanel'
import SlicePanel from './components/SlicePanel/SlicePanel'
import InsightPanel from './components/InsightPanel/InsightPanel'
import CubeView from './components/CubeView'
import GanttView from './components/GanttView'
import MatrixViewContainer from './components/MatrixView'
import ClassLibraryView from './components/ClassLibrary/ClassLibraryView'
import SettingsView from './components/Settings/SettingsView'

const SLICE_VIEWS = new Set(['graph', 'list', 'cube'])

// Keyboard shortcut → view mode
const VIEW_SHORTCUTS: Record<string, string> = {
  g: 'graph',
  l: 'list',
  c: 'cube',
  f: 'gantt',
  m: 'matrix',
}

export default function App() {
  const { viewMode, selectedEntity, sliceFilters, setViewMode, setSelectedEntity } = useAppStore()
  const { undo, redo, canUndo, canRedo } = useHistoryStore()

  const showSlicePanel = SLICE_VIEWS.has(viewMode)
  const hasActiveFilters = Object.values(sliceFilters).some((v) => v !== null)

  // Global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName
      const inInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'

      const isCtrl = e.ctrlKey || e.metaKey

      // Undo: Ctrl+Z
      if (isCtrl && e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        if (canUndo) undo()
        return
      }

      // Redo: Ctrl+Shift+Z
      if (isCtrl && e.key === 'z' && e.shiftKey) {
        e.preventDefault()
        if (canRedo) redo()
        return
      }

      // Escape: close active panel / deselect entity
      if (e.key === 'Escape') {
        setSelectedEntity(null)
        return
      }

      // View mode shortcuts (only when not in an input field)
      if (!inInput && !isCtrl && !e.altKey && !e.shiftKey) {
        const mode = VIEW_SHORTCUTS[e.key.toLowerCase()]
        if (mode) {
          e.preventDefault()
          setViewMode(mode as Parameters<typeof setViewMode>[0])
        }
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [canUndo, canRedo, undo, redo, setViewMode, setSelectedEntity])

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />

      <div className="flex flex-col flex-1 overflow-hidden">
        <TopBar />
        {showSlicePanel && <SlicePanel />}

        <div className="flex flex-1 overflow-hidden">
          {/* Main content */}
          {viewMode === 'dashboard' && <Dashboard />}
          {viewMode === 'graph' && <GraphView />}
          {viewMode === 'list' && <ListView />}
{viewMode === 'cube' && <CubeView />}
          {viewMode === 'gantt' && <GanttView />}
          {viewMode === 'matrix' && <MatrixViewContainer />}
          {viewMode === 'library' && <ClassLibraryView />}
          {viewMode === 'settings' && <SettingsView />}

          {/* Insight panel when slice filters are active */}
          {showSlicePanel && hasActiveFilters && <InsightPanel />}

          {/* Detail panel slides in when an entity is selected */}
          {selectedEntity && <DetailPanel />}
        </div>
      </div>
    </div>
  )
}
