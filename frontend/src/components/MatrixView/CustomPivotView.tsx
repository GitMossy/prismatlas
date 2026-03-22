/**
 * Custom Pivot View — FR-4.6.1, FR-4.6.2
 * User-selectable row axis, col axis, and metric.
 * Save view button persists configuration.
 */
import { useState } from 'react'
import { useAppStore } from '../../store'
import { useCustomMatrix, useCreateSavedView } from '../../hooks/useMatrix'
import MatrixView from './MatrixView'

const DIM_OPTIONS = [
  { value: 'area', label: 'Area' },
  { value: 'object_type', label: 'Object Type' },
  { value: 'zone', label: 'Zone' },
  { value: 'owner', label: 'Owner' },
  { value: 'stage', label: 'Stage' },
]

const METRIC_OPTIONS = [
  { value: 'readiness', label: 'Readiness' },
  { value: 'count', label: 'Count' },
  { value: 'complexity', label: 'Complexity' },
]

export default function CustomPivotView() {
  const { selectedProjectId } = useAppStore()
  const [rows, setRows] = useState('area')
  const [cols, setCols] = useState('object_type')
  const [metric, setMetric] = useState('readiness')
  const [viewName, setViewName] = useState('')
  const [saveMsg, setSaveMsg] = useState('')

  const { data, isLoading, isError } = useCustomMatrix(
    selectedProjectId,
    { rows, cols, metric }
  )

  const { mutate: saveView, isPending: isSaving } = useCreateSavedView(selectedProjectId ?? '')

  const handleSave = () => {
    if (!selectedProjectId || !viewName.trim()) return
    saveView(
      { name: viewName.trim(), config: { view: 'custom', rows, cols, metric } },
      {
        onSuccess: () => {
          setSaveMsg('Saved!')
          setViewName('')
          setTimeout(() => setSaveMsg(''), 3000)
        },
      }
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 px-4 py-2 bg-card border-b border-border shrink-0">
        <span className="text-xs font-medium text-foreground">Custom Pivot</span>

        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          Rows:
          <select
            value={rows}
            onChange={(e) => setRows(e.target.value)}
            className="border border-border bg-background text-foreground rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          >
            {DIM_OPTIONS.filter((o) => o.value !== cols).map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          Cols:
          <select
            value={cols}
            onChange={(e) => setCols(e.target.value)}
            className="border border-border bg-background text-foreground rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          >
            {DIM_OPTIONS.filter((o) => o.value !== rows).map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          Metric:
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            className="border border-border bg-background text-foreground rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          >
            {METRIC_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        {/* Save view */}
        <div className="flex items-center gap-1 ml-auto">
          {saveMsg && <span className="text-xs text-green-600 dark:text-green-400">{saveMsg}</span>}
          <input
            type="text"
            placeholder="View name…"
            value={viewName}
            onChange={(e) => setViewName(e.target.value)}
            className="border border-border bg-background text-foreground rounded px-2 py-0.5 text-xs w-32 focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <button
            onClick={handleSave}
            disabled={isSaving || !viewName.trim() || !selectedProjectId}
            className="px-2 py-0.5 text-xs bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            Save view
          </button>
        </div>
      </div>

      {isError && (
        <p className="text-xs text-red-500 px-4 py-2">
          Error loading matrix. Rows and cols must be different dimensions.
        </p>
      )}

      <MatrixView
        rowLabels={data?.row_labels ?? []}
        colLabels={data?.col_labels ?? []}
        cells={data?.cells ?? []}
        isLoading={isLoading}
      />
    </div>
  )
}
