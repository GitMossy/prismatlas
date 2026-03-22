import { useAppStore } from '../../store'

const STAGE_OPTIONS = [
  { value: 'engineering', label: 'Engineering' },
  { value: 'fat_prep', label: 'FAT Prep' },
  { value: 'fat_execution', label: 'FAT Execution' },
  { value: 'sat_prep', label: 'SAT Prep' },
  { value: 'sat_execution', label: 'SAT Execution' },
]

const OBJECT_TYPE_OPTIONS = ['IO', 'CM', 'EM', 'Phase', 'Recipe', 'Unit_Procedure', 'Batch', 'Other']

const inputCls = 'border border-border bg-background rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring'

export default function SlicePanel() {
  const { sliceFilters, setSliceFilters, resetSliceFilters } = useAppStore()

  const activeCount = Object.values(sliceFilters).filter((v) => v !== null).length

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-background border-b border-border flex-wrap">
      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide shrink-0">
        Filters
      </span>

      <input
        type="text"
        placeholder="Zone"
        value={sliceFilters.zone ?? ''}
        onChange={(e) => setSliceFilters({ zone: e.target.value || null })}
        className={`${inputCls} w-28`}
      />

      <select
        value={sliceFilters.stage ?? ''}
        onChange={(e) => setSliceFilters({ stage: e.target.value || null })}
        className={`${inputCls} w-36`}
      >
        <option value="">Stage (any)</option>
        {STAGE_OPTIONS.map((s) => (
          <option key={s.value} value={s.value}>{s.label}</option>
        ))}
      </select>

      <select
        value={sliceFilters.object_type ?? ''}
        onChange={(e) => setSliceFilters({ object_type: e.target.value || null })}
        className={`${inputCls} w-36`}
      >
        <option value="">Type (any)</option>
        {OBJECT_TYPE_OPTIONS.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>

      <input
        type="text"
        placeholder="Owner"
        value={sliceFilters.owner ?? ''}
        onChange={(e) => setSliceFilters({ owner: e.target.value || null })}
        className={`${inputCls} w-28`}
      />

      <div className="flex items-center gap-1">
        <span className="text-xs text-muted-foreground">From</span>
        <input
          type="date"
          value={sliceFilters.planned_after ?? ''}
          onChange={(e) => setSliceFilters({ planned_after: e.target.value || null })}
          className={inputCls}
        />
        <span className="text-xs text-muted-foreground">To</span>
        <input
          type="date"
          value={sliceFilters.planned_before ?? ''}
          onChange={(e) => setSliceFilters({ planned_before: e.target.value || null })}
          className={inputCls}
        />
      </div>

      <button
        onClick={resetSliceFilters}
        disabled={activeCount === 0}
        className="ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-muted hover:bg-muted/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Reset
        {activeCount > 0 && (
          <span className="bg-primary text-primary-foreground rounded-full w-4 h-4 flex items-center justify-center text-[10px] font-bold">
            {activeCount}
          </span>
        )}
      </button>
    </div>
  )
}
