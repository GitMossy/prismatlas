import { useSortable, SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { TaskDef } from '../../types'

function TaskRow({
  task,
  onChange,
  onRemove,
}: {
  task: TaskDef
  onChange: (t: TaskDef) => void
  onRemove: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: task.key })

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1 }}
      className="flex items-center gap-2 bg-card border border-border rounded px-2 py-1.5"
    >
      <span
        {...attributes}
        {...listeners}
        className="text-muted-foreground/40 hover:text-muted-foreground cursor-grab text-sm select-none"
      >
        ⠿
      </span>

      <input
        className="flex-1 text-xs border-0 focus:outline-none focus:ring-0 bg-transparent text-foreground"
        value={task.name}
        onChange={(e) => onChange({ ...task, name: e.target.value })}
        placeholder="Task name"
      />

      <label className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
        <input
          type="checkbox"
          checked={task.is_mandatory}
          onChange={(e) => onChange({ ...task, is_mandatory: e.target.checked })}
          className="rounded"
        />
        Mandatory
      </label>

      <button onClick={onRemove} className="text-muted-foreground/40 hover:text-red-500 text-base leading-none shrink-0">
        ×
      </button>
    </div>
  )
}

interface Props {
  tasks: TaskDef[]
  onChange: (tasks: TaskDef[]) => void
}

export default function TaskList({ tasks, onChange }: Props) {
  const addTask = () => {
    const key = `task_${Date.now()}`
    onChange([...tasks, { key, name: '', order: tasks.length + 1, is_mandatory: true }])
  }

  const updateTask = (i: number, updated: TaskDef) => {
    const next = [...tasks]
    next[i] = updated
    onChange(next)
  }

  const removeTask = (i: number) => onChange(tasks.filter((_, idx) => idx !== i))

  return (
    <div className="space-y-1.5">
      <SortableContext items={tasks.map((t) => t.key)} strategy={verticalListSortingStrategy}>
        {tasks.map((t, i) => (
          <TaskRow
            key={t.key}
            task={t}
            onChange={(u) => updateTask(i, u)}
            onRemove={() => removeTask(i)}
          />
        ))}
      </SortableContext>

      <button
        onClick={addTask}
        className="w-full text-xs text-primary hover:text-primary/80 border border-dashed border-primary/30 rounded py-1.5 hover:border-primary transition-colors"
      >
        + Add task
      </button>
    </div>
  )
}
