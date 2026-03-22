/**
 * Resource Loading Histogram — FR-4.6.2
 * Rows = resources, Cols = time buckets.
 * Color: green (<80% capacity), amber (80–100%), red (>100%).
 */
import { useState } from 'react'
import { useAppStore } from '../../store'
import { useResourceLoading } from '../../hooks/useMatrix'
import MatrixView from './MatrixView'

export default function ResourceLoadingHistogram() {
  const { selectedProjectId } = useAppStore()
  const [startDay, setStartDay] = useState(0)
  const [endDay, setEndDay] = useState(90)
  const [bucket, setBucket] = useState<'week' | 'month'>('week')

  const { data, isLoading } = useResourceLoading(selectedProjectId, {
    start_day: startDay,
    end_day: endDay,
    bucket,
  })

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Controls */}
      <div className="flex items-center gap-4 px-4 py-2 bg-card border-b border-border shrink-0">
        <span className="text-xs font-medium text-foreground">Resource Loading</span>
        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          Start day:
          <input
            type="number"
            value={startDay}
            min={0}
            onChange={(e) => setStartDay(Number(e.target.value))}
            className="w-16 border border-border bg-background text-foreground rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </label>
        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          End day:
          <input
            type="number"
            value={endDay}
            min={1}
            onChange={(e) => setEndDay(Number(e.target.value))}
            className="w-16 border border-border bg-background text-foreground rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </label>
        <label className="flex items-center gap-1 text-xs text-muted-foreground">
          Bucket:
          <select
            value={bucket}
            onChange={(e) => setBucket(e.target.value as 'week' | 'month')}
            className="border border-border bg-background text-foreground rounded px-1 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="week">Week</option>
            <option value="month">Month</option>
          </select>
        </label>
        <span className="text-xs text-muted-foreground/60 ml-2">
          Green &lt;80% · Amber 80–100% · Red &gt;100%
        </span>
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
