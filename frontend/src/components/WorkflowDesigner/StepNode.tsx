/**
 * StepNode — React Flow custom node for a workflow stage.
 * Shows stage name, task count, mandatory badge.
 * Visual treatment for root (no predecessors) vs connected stages.
 */
import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import type { StageDef } from '../../types'

export interface StepNodeData {
  stage: StageDef
  isRoot: boolean
}

function StepNode({ data, selected }: NodeProps<StepNodeData>) {
  const { stage, isRoot } = data
  const taskCount = stage.tasks.length

  return (
    <div
      className={`
        relative rounded-lg border-2 px-3 py-2 min-w-[140px] shadow-sm text-left
        ${selected ? 'border-primary bg-primary/10' : isRoot ? 'border-green-400 bg-green-50 dark:bg-green-900/20' : 'border-border bg-card'}
        transition-colors
      `}
    >
      {/* Input handle (top) */}
      {!isRoot && (
        <Handle
          type="target"
          position={Position.Top}
          className="!w-3 !h-3 !bg-muted-foreground !border-card"
        />
      )}

      {/* Stage name */}
      <p className="text-xs font-semibold text-foreground truncate max-w-[160px]" title={stage.name}>
        {stage.name || <span className="text-muted-foreground italic">Unnamed</span>}
      </p>

      {/* Meta row */}
      <div className="flex items-center gap-1.5 mt-1">
        <span className="text-xs text-muted-foreground">{taskCount} task{taskCount !== 1 ? 's' : ''}</span>
        {stage.is_mandatory && (
          <span className="px-1 py-0.5 text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded font-medium">
            Mandatory
          </span>
        )}
        {isRoot && (
          <span className="px-1 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded font-medium">
            Start
          </span>
        )}
      </div>

      {/* Criteria badge */}
      {stage.entry_criteria.length > 0 && (
        <p className="mt-1 text-xs text-muted-foreground/60 truncate">
          {stage.entry_criteria.length} entr{stage.entry_criteria.length !== 1 ? 'y criteria' : 'y criterion'}
        </p>
      )}

      {/* Output handle (bottom) */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-muted-foreground !border-card"
      />
    </div>
  )
}

export default memo(StepNode)
