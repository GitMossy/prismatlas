/**
 * Area Heatmap — FR-4.6.2
 * Rows = object types, Cols = areas.
 * Metric selector: complexity | readiness | count.
 */
import { useState } from 'react'
import { useAppStore } from '../../store'
import { useAreaHeatmap } from '../../hooks/useMatrix'
import MatrixView from './MatrixView'

type Metric = 'complexity' | 'readiness' | 'count'

export default function AreaHeatmap() {
  const { selectedProjectId } = useAppStore()
  const [metric, setMetric] = useState<Metric>('readiness')
  const { data, isLoading } = useAreaHeatmap(selectedProjectId, metric)

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="flex items-center gap-4 px-4 py-2 bg-card border-b border-border shrink-0">
        <span className="text-xs font-medium text-foreground">Area Heatmap</span>
        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          Metric:
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as Metric)}
            className="border border-border bg-background text-foreground rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="readiness">Readiness</option>
            <option value="complexity">Complexity</option>
            <option value="count">Count</option>
          </select>
        </label>
      </div>

      <MatrixView
        rowLabels={data?.row_labels ?? []}
        colLabels={data?.col_labels ?? []}
        cells={data?.cells ?? []}
        isLoading={isLoading}
      />
    </div>
  )
}
