/**
 * Deliverable Register — FR-4.6.1f
 *
 * Rows = deliverable names, Cols = status stages.
 * Colour encodes the current deliverable status.
 *
 * Status colour map:
 *   not_started → gray
 *   in_progress → blue
 *   in_review   → amber
 *   approved    → green
 *   rejected    → red
 */
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import MatrixView from './MatrixView'
import type { MatrixCell } from '../../types'

const STATUS_COLORS: Record<string, string> = {
  not_started: '#9ca3af',
  in_progress: '#3b82f6',
  in_review:   '#f59e0b',
  approved:    '#22c55e',
  rejected:    '#ef4444',
}

const STATUS_ORDER = ['not_started', 'in_progress', 'in_review', 'approved', 'rejected']

interface Deliverable {
  id: string
  name: string
  status: string
  stage_key: string | null
  due_date: string | null
  assigned_to: string | null
}

function buildMatrix(deliverables: Deliverable[]) {
  const rowLabels = [...new Set(deliverables.map((d) => d.name))]
  const colLabels = STATUS_ORDER

  const cells: MatrixCell[] = deliverables.map((d) => ({
    row: d.name,
    col: d.status,
    value: d.assigned_to ?? d.stage_key ?? '—',
    color: STATUS_COLORS[d.status] ?? '#9ca3af',
  }))

  return { rowLabels, colLabels, cells }
}

export default function DeliverableRegister() {
  const { selectedProjectId } = useAppStore()

  const { data: deliverables = [], isLoading } = useQuery<Deliverable[]>({
    queryKey: ['deliverables', selectedProjectId],
    queryFn: async () => {
      if (!selectedProjectId) return []
      // Import client lazily to keep component self-contained
      const { default: client } = await import('../../api/client')
      const res = await client.get(`/deliverables`, { params: { project_id: selectedProjectId } })
      return res.data
    },
    enabled: !!selectedProjectId,
  })

  const { rowLabels, colLabels, cells } = buildMatrix(deliverables)

  return (
    <MatrixView
      title="Deliverable Register"
      rowLabels={rowLabels}
      colLabels={colLabels}
      cells={cells}
      isLoading={isLoading}
    />
  )
}
