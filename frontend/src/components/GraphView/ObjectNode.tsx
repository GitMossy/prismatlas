import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import type { NodeProps } from 'reactflow'

export interface ObjectNodeData {
  label: string
  objectType: string
  status: string
  readiness: number | null
  hasBlockers: boolean
  onWhyBlocked: () => void
}

function statusColour(readiness: number | null, hasBlockers: boolean) {
  if (readiness === null) return { border: 'border-border', bg: 'bg-card', text: 'text-muted-foreground' }
  if (hasBlockers || readiness < 0.5) return { border: 'border-red-400', bg: 'bg-red-50 dark:bg-red-900/20', text: 'text-red-700 dark:text-red-400' }
  if (readiness < 0.9) return { border: 'border-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-400' }
  return { border: 'border-green-400', bg: 'bg-green-50 dark:bg-green-900/20', text: 'text-green-700 dark:text-green-400' }
}

const ObjectNode = memo(({ data }: NodeProps<ObjectNodeData>) => {
  const { border, bg, text } = statusColour(data.readiness, data.hasBlockers)
  const pct = data.readiness !== null ? Math.round(data.readiness * 100) : null

  return (
    <div className={`rounded-lg border-2 ${border} ${bg} px-3 py-2 w-44 shadow-sm`}>
      <Handle type="target" position={Position.Left} className="!bg-muted-foreground" />
      <div className="flex items-center justify-between gap-1">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-foreground truncate">{data.label}</p>
          <p className="text-xs text-muted-foreground">{data.objectType}</p>
        </div>
        {pct !== null && (
          <span className={`text-xs font-bold shrink-0 ${text}`}>{pct}%</span>
        )}
      </div>
      {data.hasBlockers && (
        <button
          onClick={(e) => { e.stopPropagation(); data.onWhyBlocked() }}
          className="mt-1.5 text-xs text-red-600 dark:text-red-400 underline hover:text-red-800 dark:hover:text-red-300"
        >
          Why blocked?
        </button>
      )}
      <Handle type="source" position={Position.Right} className="!bg-muted-foreground" />
    </div>
  )
})

ObjectNode.displayName = 'ObjectNode'
export default ObjectNode
