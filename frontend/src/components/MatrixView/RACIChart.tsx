/**
 * RACI Chart — FR-4.6.1h
 *
 * Rows = RBS roles/resources, Cols = activities (ABS step keys).
 * Cell value = RACI assignment (R / A / C / I).
 *
 * Colour map:
 *   R (Responsible) → blue
 *   A (Accountable) → green
 *   C (Consulted)   → amber
 *   I (Informed)    → gray
 *
 * Data source: task_instances joined with resources via assigned_resource_id.
 * For Phase 6 this is a read-only view derived from workflow instances.
 */
import { useAppStore } from '../../store'
import { useRACIMatrix } from '../../hooks/useMatrix'
import MatrixView from './MatrixView'
import type { MatrixCell } from '../../types'

const RACI_COLORS: Record<string, string> = {
  R: '#3b82f6',
  A: '#22c55e',
  C: '#f59e0b',
  I: '#9ca3af',
}

interface RACIRow {
  resource_name: string
  step_key: string
  raci_role: 'R' | 'A' | 'C' | 'I'
}

function buildMatrix(rows: RACIRow[]) {
  const resourceNames = [...new Set(rows.map((r) => r.resource_name))]
  const stepKeys = [...new Set(rows.map((r) => r.step_key))]

  const cells: MatrixCell[] = rows.map((r) => ({
    row: r.resource_name,
    col: r.step_key,
    value: r.raci_role,
    color: RACI_COLORS[r.raci_role] ?? '#9ca3af',
  }))

  return { rowLabels: resourceNames, colLabels: stepKeys, cells }
}

export default function RACIChart() {
  const { selectedProjectId } = useAppStore()
  const { data: raciRows = [], isLoading } = useRACIMatrix(selectedProjectId)

  const { rowLabels, colLabels, cells } = buildMatrix(raciRows)

  return (
    <MatrixView
      title="RACI Chart (RBS × ABS)"
      rowLabels={rowLabels}
      colLabels={colLabels}
      cells={cells}
      isLoading={isLoading}
    />
  )
}
