/**
 * Matrix view container — routes between sub-views based on matrixConfig.view.
 * Renders when viewMode === 'matrix'.
 *
 * V3 additions: Deliverable Register (FR-4.6.1f), RACI Chart (FR-4.6.1h),
 *               Resource Assignment (FR-4.6.1d).
 */
import { useAppStore } from '../../store'
import TaskStatusMatrix from './TaskStatusMatrix'
import ResourceLoadingHistogram from './ResourceLoadingHistogram'
import AreaHeatmap from './AreaHeatmap'
import CustomPivotView from './CustomPivotView'
import DeliverableRegister from './DeliverableRegister'
import RACIChart from './RACIChart'
import ResourceAssignment from './ResourceAssignment'

const TABS = [
  { key: 'task-status',         label: 'Task Status' },
  { key: 'resource-loading',    label: 'Resource Loading' },
  { key: 'area-heatmap',        label: 'Area Heatmap' },
  { key: 'deliverable-register', label: 'Deliverables' },
  { key: 'raci',                label: 'RACI' },
  { key: 'resource-assignment', label: 'Resource Assignment' },
  { key: 'custom',              label: 'Custom Pivot' },
]

export default function MatrixViewContainer() {
  const { matrixConfig, setMatrixConfig, selectedProjectId } = useAppStore()

  if (!selectedProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        Select a project to view matrices.
      </div>
    )
  }

  const activeView = matrixConfig.view

  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-background">
      {/* Tab bar */}
      <div className="flex gap-1 px-4 pt-3 border-b border-border shrink-0 bg-card overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setMatrixConfig({ view: tab.key })}
            className={`pb-2 px-3 text-sm border-b-2 transition-colors whitespace-nowrap ${
              activeView === tab.key
                ? 'border-primary text-primary font-medium'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {activeView === 'task-status'          && <TaskStatusMatrix />}
        {activeView === 'resource-loading'     && <ResourceLoadingHistogram />}
        {activeView === 'area-heatmap'         && <AreaHeatmap />}
        {activeView === 'deliverable-register' && <DeliverableRegister />}
        {activeView === 'raci'                 && <RACIChart />}
        {activeView === 'resource-assignment'  && <ResourceAssignment />}
        {activeView === 'custom'               && <CustomPivotView />}
      </div>
    </div>
  )
}
