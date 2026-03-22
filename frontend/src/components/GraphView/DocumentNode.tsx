import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import type { NodeProps } from 'reactflow'

export interface DocumentNodeData {
  label: string
  documentType: string
  status: string
}

const STATUS_STYLE: Record<string, { border: string; bg: string; text: string }> = {
  Approved:    { border: 'border-green-400', bg: 'bg-green-50 dark:bg-green-900/20',   text: 'text-green-700 dark:text-green-400' },
  In_Review:   { border: 'border-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/20',   text: 'text-amber-700 dark:text-amber-400' },
  Draft:       { border: 'border-border',    bg: 'bg-card',                             text: 'text-muted-foreground' },
  Superseded:  { border: 'border-border',    bg: 'bg-card',                             text: 'text-muted-foreground/60' },
  Obsolete:    { border: 'border-border',    bg: 'bg-card',                             text: 'text-muted-foreground/60' },
}

const DocumentNode = memo(({ data }: NodeProps<DocumentNodeData>) => {
  const style = STATUS_STYLE[data.status] ?? STATUS_STYLE['Draft']

  return (
    <div className={`rounded border-2 border-dashed ${style.border} ${style.bg} px-3 py-2 w-44 shadow-sm`}>
      <Handle type="target" position={Position.Left} className="!bg-muted-foreground" />
      <div>
        <p className="text-xs font-semibold text-foreground truncate">{data.label}</p>
        <div className="flex items-center justify-between mt-0.5">
          <p className="text-xs text-muted-foreground">{data.documentType}</p>
          <span className={`text-xs font-medium ${style.text}`}>{data.status}</span>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-muted-foreground" />
    </div>
  )
})

DocumentNode.displayName = 'DocumentNode'
export default DocumentNode
