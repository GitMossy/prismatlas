/**
 * Resource Assignment View — FR-4.6.1d
 *
 * Rows = Resources (RBS), Cols = CBS items / class names.
 * Cell = % allocation (0–100).
 *
 * Colour scale:
 *   0%     → white
 *   1–50%  → blue gradient
 *   51–80% → amber
 *   81%+   → red (over-allocation risk)
 */
import { useAppStore } from '../../store'
import { useResourceAssignment } from '../../hooks/useMatrix'
import MatrixView from './MatrixView'
import type { MatrixCell } from '../../types'

interface AllocationCell {
  resource_name: string
  cbs_item: string
  allocation_pct: number
}

function allocationColor(pct: number): string {
  if (pct === 0) return '#f8fafc'
  if (pct <= 50) return `hsl(210, 80%, ${Math.round(80 - pct * 0.6)}%)`
  if (pct <= 80) return '#f59e0b'
  return '#ef4444'
}

function buildMatrix(rows: AllocationCell[]) {
  const resourceNames = [...new Set(rows.map((r) => r.resource_name))]
  const cbsItems = [...new Set(rows.map((r) => r.cbs_item))]

  const cells: MatrixCell[] = rows.map((r) => ({
    row: r.resource_name,
    col: r.cbs_item,
    value: r.allocation_pct,
    color: allocationColor(r.allocation_pct),
  }))

  return { rowLabels: resourceNames, colLabels: cbsItems, cells }
}

export default function ResourceAssignment() {
  const { selectedProjectId } = useAppStore()
  const { data: allocationRows = [], isLoading } = useResourceAssignment(selectedProjectId)

  const { rowLabels, colLabels, cells } = buildMatrix(allocationRows)

  return (
    <MatrixView
      title="Resource Assignment (RBS × CBS — % Allocation)"
      rowLabels={rowLabels}
      colLabels={colLabels}
      cells={cells}
      isLoading={isLoading}
    />
  )
}
