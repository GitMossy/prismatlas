/**
 * GanttView — FR-4.4.2 / FR-4.6
 *
 * Renders a horizontal bar chart for workflow task instances ordered by stage
 * and task order. Each bar spans from early_start to early_finish (day offsets).
 * Critical-path tasks are highlighted in red; non-critical in blue.
 *
 * The view works per workflow instance. The user selects an entity (object)
 * from the entity picker, then we fetch its workflow instance and CPM schedule.
 *
 * Export buttons trigger CSV downloads directly from the backend.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import { scheduleApi, exportApi } from '../../api/schedule'
import client from '../../api/client'
import type { WorkflowInstance, TaskScheduleRow } from '../../types'

const DAY_PX = 24          // pixels per day column
const ROW_HEIGHT = 36      // px per task row
const LABEL_WIDTH = 280    // px for task name column

// Colour palette
const CRITICAL_BG = 'bg-red-500'
const CRITICAL_TEXT = 'text-red-700'
const NORMAL_BG = 'bg-blue-500'
const FLOAT_BG = 'bg-blue-200'

function fetchWorkflowInstance(entityId: string): Promise<WorkflowInstance> {
  return client.get(`/entities/${entityId}/workflow`).then((r) => r.data)
}

interface GanttBarProps {
  task: TaskScheduleRow
  projectDuration: number
}

function GanttBar({ task, projectDuration }: GanttBarProps) {
  const es = task.early_start ?? 0
  const ef = task.early_finish ?? (es + (task.duration_days ?? 1))
  const ls = task.late_start ?? es
  const width = Math.max(ef - es, 1)
  const floatWidth = Math.max(ls - es, 0)
  const isCritical = task.is_critical

  const leftPx = es * DAY_PX
  const widthPx = width * DAY_PX
  const floatPx = floatWidth * DAY_PX

  return (
    <div className="relative" style={{ width: projectDuration * DAY_PX, height: ROW_HEIGHT }}>
      {/* Float bar (behind) */}
      {floatPx > 0 && (
        <div
          className={`absolute top-2 bottom-2 rounded opacity-50 ${FLOAT_BG}`}
          style={{ left: leftPx, width: floatPx + widthPx }}
        />
      )}
      {/* Duration bar */}
      <div
        className={`absolute top-2 bottom-2 rounded ${isCritical ? CRITICAL_BG : NORMAL_BG} flex items-center px-1 overflow-hidden`}
        style={{ left: leftPx, width: widthPx }}
        title={`${task.task_name} | ES:${es} EF:${ef} LS:${ls} Float:${task.total_float ?? '?'}`}
      >
        {widthPx > 40 && (
          <span className="text-white text-xs font-medium truncate">{task.task_name}</span>
        )}
      </div>
    </div>
  )
}

export default function GanttView() {
  const { selectedProjectId, selectedEntity } = useAppStore()
  const queryClient = useQueryClient()

  // Fetch the workflow instance for the selected entity
  const { data: workflowInstance, isLoading: loadingInstance } = useQuery({
    queryKey: ['workflow-instance', selectedEntity?.id],
    queryFn: () => fetchWorkflowInstance(selectedEntity!.id),
    enabled: !!selectedEntity,
  })

  // Fetch CPM schedule for the instance
  const { data: schedule, isLoading: loadingSchedule } = useQuery({
    queryKey: ['schedule', workflowInstance?.id],
    queryFn: () => scheduleApi.getSchedule(workflowInstance!.id),
    enabled: !!workflowInstance?.id,
  })

  const runCpm = useMutation({
    mutationFn: () => scheduleApi.runCpm(workflowInstance!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule', workflowInstance?.id] })
    },
  })

  if (!selectedEntity) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        Select an object in the hierarchy or list to view its Gantt schedule.
      </div>
    )
  }

  if (loadingInstance || loadingSchedule) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        Loading schedule…
      </div>
    )
  }

  if (!workflowInstance) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground">
        This entity has no active workflow instance.
      </div>
    )
  }

  const projectDuration = schedule?.project_duration_days ?? 0
  const tasks = schedule?.tasks ?? []
  const criticalCount = tasks.filter((t) => t.is_critical).length

  // Group tasks by stage for row headers
  const stageGroups: Record<string, { stageName: string; tasks: TaskScheduleRow[] }> = {}
  for (const task of tasks) {
    if (!stageGroups[task.stage_key]) {
      stageGroups[task.stage_key] = { stageName: task.stage_name, tasks: [] }
    }
    stageGroups[task.stage_key].tasks.push(task)
  }

  // Build day columns for the header
  const dayColumns = Array.from({ length: projectDuration }, (_, i) => i)

  return (
    <div className="flex flex-col flex-1 overflow-hidden bg-background">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border bg-card">
        <h2 className="text-sm font-semibold text-foreground">
          Gantt — {selectedEntity.type} workflow
        </h2>

        <span className="text-xs text-muted-foreground">
          {tasks.length} tasks · {projectDuration} days · {criticalCount} critical
        </span>

        <div className="ml-auto flex gap-2">
          <button
            onClick={() => runCpm.mutate()}
            disabled={runCpm.isPending}
            className="px-3 py-1 text-xs bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
          >
            {runCpm.isPending ? 'Running…' : 'Recalculate CPM'}
          </button>

          {selectedProjectId && (
            <>
              <a
                href={`http://localhost:8000${exportApi.tasksCsvUrl(selectedProjectId)}`}
                download
                className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
              >
                Export Tasks CSV
              </a>
              <a
                href={`http://localhost:8000${exportApi.objectsCsvUrl(selectedProjectId)}`}
                download
                className="px-3 py-1 text-xs bg-muted text-foreground rounded hover:bg-accent border border-border"
              >
                Export Objects CSV
              </a>
            </>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 px-4 py-1 border-b border-border text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block w-4 h-3 rounded bg-red-500" /> Critical path
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-4 h-3 rounded bg-blue-500" /> Non-critical
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-4 h-3 rounded bg-blue-200" /> Float
        </span>
      </div>

      {tasks.length === 0 && (
        <div className="flex flex-1 items-center justify-center text-muted-foreground">
          No schedule data. Set task durations and click "Recalculate CPM".
        </div>
      )}

      {tasks.length > 0 && (
        <div className="flex flex-1 overflow-auto">
          {/* Task label column */}
          <div className="flex-shrink-0 border-r border-border" style={{ width: LABEL_WIDTH }}>
            {/* Header spacer */}
            <div className="h-8 border-b border-border bg-muted/50 flex items-center px-3">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Task</span>
            </div>
            {Object.entries(stageGroups).map(([stageKey, { stageName, tasks: stageTasks }]) => (
              <div key={stageKey}>
                {/* Stage header */}
                <div className="px-3 py-1 bg-muted border-b border-border">
                  <span className="text-xs font-semibold text-foreground">{stageName}</span>
                </div>
                {stageTasks.map((task) => (
                  <div
                    key={task.task_id}
                    className="flex items-center px-3 border-b border-border/50"
                    style={{ height: ROW_HEIGHT }}
                  >
                    <span
                      className={`text-xs truncate ${task.is_critical ? CRITICAL_TEXT + ' font-semibold' : 'text-foreground'}`}
                      title={task.task_name}
                    >
                      {task.task_name}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>

          {/* Gantt chart area */}
          <div className="overflow-x-auto flex-1">
            {/* Day header */}
            <div className="flex h-8 border-b border-border bg-muted/50 sticky top-0 z-10">
              {dayColumns.map((day) => (
                <div
                  key={day}
                  className="flex-shrink-0 border-r border-border flex items-center justify-center"
                  style={{ width: DAY_PX }}
                >
                  {day % 5 === 0 && (
                    <span className="text-xs text-muted-foreground">{day}</span>
                  )}
                </div>
              ))}
            </div>

            {/* Task rows */}
            {Object.entries(stageGroups).map(([stageKey, { stageName: _stageName, tasks: stageTasks }]) => (
              <div key={stageKey}>
                {/* Stage header spacer */}
                <div
                  className="border-b border-border bg-muted"
                  style={{ height: 24, width: projectDuration * DAY_PX }}
                />
                {stageTasks.map((task) => (
                  <div
                    key={task.task_id}
                    className="border-b border-border/50 relative"
                    style={{ height: ROW_HEIGHT, width: projectDuration * DAY_PX }}
                  >
                    {/* Grid lines every 5 days */}
                    {dayColumns
                      .filter((d) => d % 5 === 0)
                      .map((d) => (
                        <div
                          key={d}
                          className="absolute top-0 bottom-0 border-l border-border/30"
                          style={{ left: d * DAY_PX }}
                        />
                      ))}
                    <GanttBar task={task} projectDuration={projectDuration} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
