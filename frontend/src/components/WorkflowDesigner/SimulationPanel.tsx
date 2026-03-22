import { useState } from 'react'
import type { TemplateDef, StageDef } from '../../types'

interface SimState {
  completedTasks: Set<string>
}

function stageIsAccessible(stage: StageDef, allStages: StageDef[], simState: SimState): boolean {
  for (const criterion of stage.entry_criteria) {
    if (criterion.type === 'stage_complete') {
      const dep = allStages.find((s) => s.key === criterion.stage_key)
      if (!dep) return false
      const depTasks = dep.tasks.filter((t) => t.is_mandatory)
      if (!depTasks.every((t) => simState.completedTasks.has(`${dep.key}.${t.key}`))) return false
    }
  }
  return true
}

function stageExitMet(stage: StageDef, simState: SimState): boolean {
  for (const criterion of stage.exit_criteria) {
    if (criterion.type === 'all_tasks_complete') {
      const mandatory = stage.tasks.filter((t) => t.is_mandatory)
      if (!mandatory.every((t) => simState.completedTasks.has(`${stage.key}.${t.key}`))) return false
    }
  }
  return true
}

export default function SimulationPanel({ definition }: { definition: TemplateDef }) {
  const [simState, setSimState] = useState<SimState>({ completedTasks: new Set() })

  const toggle = (stageKey: string, taskKey: string) => {
    const id = `${stageKey}.${taskKey}`
    setSimState((prev) => {
      const next = new Set(prev.completedTasks)
      next.has(id) ? next.delete(id) : next.add(id)
      return { completedTasks: next }
    })
  }

  const reset = () => setSimState({ completedTasks: new Set() })

  const stages = [...definition.stages].sort((a, b) => a.order - b.order)

  const technicalDone = stages.flatMap((s) => s.tasks.filter((t) => t.is_mandatory)).length
  const technicalComplete = [...simState.completedTasks].length
  const technicalPct = technicalDone === 0 ? 100 : Math.round((technicalComplete / technicalDone) * 100)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">
            Technical readiness: <span className="text-primary">{technicalPct}%</span>
          </p>
          <p className="text-xs text-muted-foreground">Toggle tasks to simulate progress</p>
        </div>
        <button onClick={reset} className="text-xs text-muted-foreground hover:text-foreground">Reset</button>
      </div>

      <div className="space-y-3">
        {stages.map((stage) => {
          const accessible = stageIsAccessible(stage, stages, simState)
          const exitMet = stageExitMet(stage, simState)

          return (
            <div
              key={stage.key}
              className={`rounded-lg border p-3 ${
                !accessible ? 'border-border bg-muted/30 opacity-60' :
                exitMet ? 'border-green-300 bg-green-50 dark:bg-green-900/20' :
                'border-primary/30 bg-primary/5'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium text-foreground">{stage.name}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${
                  !accessible ? 'bg-muted text-muted-foreground' :
                  exitMet ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' :
                  'bg-primary/10 text-primary'
                }`}>
                  {!accessible ? 'Locked' : exitMet ? 'Complete' : 'Active'}
                </span>
                {!stage.is_mandatory && (
                  <span className="text-xs text-muted-foreground">(optional)</span>
                )}
              </div>

              <div className="space-y-1.5">
                {stage.tasks.map((task) => {
                  const id = `${stage.key}.${task.key}`
                  const done = simState.completedTasks.has(id)
                  return (
                    <label
                      key={task.key}
                      className={`flex items-center gap-2 text-xs cursor-pointer ${!accessible ? 'cursor-not-allowed' : ''}`}
                    >
                      <input
                        type="checkbox"
                        checked={done}
                        disabled={!accessible}
                        onChange={() => toggle(stage.key, task.key)}
                        className="rounded"
                      />
                      <span className={done ? 'line-through text-muted-foreground' : 'text-foreground'}>
                        {task.name || task.key}
                      </span>
                      {!task.is_mandatory && <span className="text-muted-foreground/50">(optional)</span>}
                    </label>
                  )
                })}
                {stage.tasks.length === 0 && (
                  <p className="text-xs text-muted-foreground italic">No tasks defined</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
