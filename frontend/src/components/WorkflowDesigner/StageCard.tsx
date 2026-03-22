import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { DndContext, closestCenter, type DragEndEvent } from '@dnd-kit/core'
import { arrayMove } from '@dnd-kit/sortable'
import type { StageDef } from '../../types'
import TaskList from './TaskList'
import RuleBuilder from './RuleBuilder'
import { useState } from 'react'

interface Props {
  stage: StageDef
  allStageKeys: string[]
  onChange: (updated: StageDef) => void
  onRemove: () => void
}

export default function StageCard({ stage, allStageKeys, onChange, onRemove }: Props) {
  const [expanded, setExpanded] = useState(true)

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: stage.key })

  const handleTaskDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIdx = stage.tasks.findIndex((t) => t.key === active.id)
    const newIdx = stage.tasks.findIndex((t) => t.key === over.id)
    const reordered = arrayMove(stage.tasks, oldIdx, newIdx).map((t, i) => ({ ...t, order: i + 1 }))
    onChange({ ...stage, tasks: reordered })
  }

  const otherStageKeys = allStageKeys.filter((k) => k !== stage.key)

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1 }}
      className="bg-card border border-border rounded-lg shadow-sm"
    >
      {/* Stage header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border">
        <span
          {...attributes}
          {...listeners}
          className="text-muted-foreground/40 hover:text-muted-foreground cursor-grab text-base select-none"
        >
          ⠿
        </span>

        <input
          className="flex-1 text-sm font-medium text-foreground border-0 focus:outline-none focus:ring-0 bg-transparent"
          value={stage.name}
          onChange={(e) => onChange({ ...stage, name: e.target.value })}
          placeholder="Stage name"
        />

        <label className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
          <input
            type="checkbox"
            checked={stage.is_mandatory}
            onChange={(e) => onChange({ ...stage, is_mandatory: e.target.checked })}
            className="rounded"
          />
          Mandatory
        </label>

        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-muted-foreground hover:text-foreground text-xs px-1"
        >
          {expanded ? '▲' : '▼'}
        </button>

        <button onClick={onRemove} className="text-muted-foreground/40 hover:text-red-500 text-base leading-none">
          ×
        </button>
      </div>

      {expanded && (
        <div className="p-3 space-y-4">
          {/* Entry criteria */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-amber-600 uppercase tracking-wide">Entry criteria</span>
              <div className="flex-1 border-t border-amber-100" />
            </div>
            <RuleBuilder
              criteria={stage.entry_criteria}
              stageKeys={otherStageKeys}
              onChange={(entry_criteria) => onChange({ ...stage, entry_criteria })}
            />
          </div>

          {/* Tasks */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-blue-600 uppercase tracking-wide">Tasks</span>
              <div className="flex-1 border-t border-blue-100" />
            </div>
            <DndContext collisionDetection={closestCenter} onDragEnd={handleTaskDragEnd}>
              <TaskList
                tasks={stage.tasks}
                onChange={(tasks) => onChange({ ...stage, tasks })}
              />
            </DndContext>
          </div>

          {/* Exit criteria */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-semibold text-green-600 uppercase tracking-wide">Exit criteria</span>
              <div className="flex-1 border-t border-green-100" />
            </div>
            <RuleBuilder
              criteria={stage.exit_criteria}
              stageKeys={otherStageKeys}
              onChange={(exit_criteria) => onChange({ ...stage, exit_criteria })}
            />
          </div>
        </div>
      )}
    </div>
  )
}
