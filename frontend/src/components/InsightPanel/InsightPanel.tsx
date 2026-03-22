import { useAppStore } from '../../store'
import { useSliceQuery } from '../../hooks/useSlice'

function ReadinessBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 90 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-muted rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground w-8 text-right">{pct}%</span>
    </div>
  )
}

export default function InsightPanel() {
  const { selectedProjectId, sliceFilters, setSelectedEntity } = useAppStore()
  const { data, isLoading } = useSliceQuery(selectedProjectId, sliceFilters)

  return (
    <aside className="w-72 bg-card border-l border-border flex flex-col overflow-hidden shrink-0">
      <div className="px-4 py-3 border-b border-border bg-muted/50">
        <h2 className="text-sm font-semibold text-foreground">Slice Insights</h2>
        {data && (
          <p className="text-xs text-muted-foreground mt-0.5">{data.total} entities matched</p>
        )}
      </div>

      {isLoading && (
        <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
          Loading…
        </div>
      )}

      {data && (
        <div className="flex-1 overflow-auto">
          <div className="p-4 border-b border-border space-y-3">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Avg Readiness</p>
              <ReadinessBar value={data.avg_readiness} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-green-50 dark:bg-green-900/20 rounded p-2 text-center">
                <p className="text-lg font-semibold text-green-700 dark:text-green-400">{data.fat_ready_count}</p>
                <p className="text-xs text-green-600 dark:text-green-400">FAT Ready</p>
              </div>
              <div className="bg-primary/5 rounded p-2 text-center">
                <p className="text-lg font-semibold text-primary">{data.sat_ready_count}</p>
                <p className="text-xs text-primary/80">SAT Ready</p>
              </div>
            </div>
            {data.total_blockers > 0 && (
              <div className="bg-red-50 dark:bg-red-900/20 rounded p-2">
                <p className="text-xs text-red-600 dark:text-red-400 font-medium">{data.total_blockers} total blockers</p>
                {data.common_blocker_types.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {data.common_blocker_types.map((t) => (
                      <span key={t} className="text-[10px] bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-1.5 py-0.5 rounded">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="divide-y divide-border">
            {data.results.map((item) => (
              <button
                key={item.entity_id}
                onClick={() => setSelectedEntity({ id: item.entity_id, type: 'object' })}
                className="w-full text-left px-4 py-3 hover:bg-accent/40 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs font-medium text-foreground truncate">{item.entity_name}</p>
                  {item.current_stage && (
                    <span className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded shrink-0">
                      {item.current_stage}
                    </span>
                  )}
                </div>
                <ReadinessBar value={item.overall_readiness} />
                {item.top_blocker && (
                  <p className="text-[10px] text-red-500 mt-1 truncate">{item.top_blocker}</p>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </aside>
  )
}
