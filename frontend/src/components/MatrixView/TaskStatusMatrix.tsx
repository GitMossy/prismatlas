/**
 * Task Status Matrix — FR-4.6.1
 * Rows = objects, Cols = stage keys.
 * pending=gray, active=blue, complete=green.
 */
import { useAppStore } from '../../store'
import { useTaskStatusMatrix } from '../../hooks/useMatrix'
import MatrixView from './MatrixView'

export default function TaskStatusMatrix() {
  const { selectedProjectId } = useAppStore()
  const { data, isLoading } = useTaskStatusMatrix(selectedProjectId)

  return (
    <MatrixView
      title="Task Status by Object & Stage"
      rowLabels={data?.row_labels ?? []}
      colLabels={data?.col_labels ?? []}
      cells={data?.cells ?? []}
      isLoading={isLoading}
    />
  )
}
