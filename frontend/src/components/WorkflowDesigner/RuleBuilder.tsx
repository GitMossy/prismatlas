import type { CriterionDef } from '../../types'

const CRITERION_TYPES = [
  { value: 'all_tasks_complete', label: 'All tasks complete' },
  { value: 'stage_complete', label: 'Stage complete' },
  { value: 'document_status', label: 'Document in status' },
  { value: 'manual_approval', label: 'Manual approval required' },
]

const DOCUMENT_STATUSES = ['Draft', 'In_Review', 'Approved', 'Superseded']

interface CriterionRowProps {
  criterion: CriterionDef
  stageKeys: string[]
  onChange: (updated: CriterionDef) => void
  onRemove: () => void
}

function CriterionRow({ criterion, stageKeys, onChange, onRemove }: CriterionRowProps) {
  return (
    <div className="flex items-start gap-2 p-2 bg-muted/50 rounded border border-border">
      <div className="flex-1 space-y-1.5">
        <select
          className="w-full border border-border rounded px-2 py-1 text-xs bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          value={criterion.type}
          onChange={(e) => onChange({ type: e.target.value })}
        >
          {CRITERION_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>

        {criterion.type === 'stage_complete' && (
          <select
            className="w-full border border-border rounded px-2 py-1 text-xs bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            value={criterion.stage_key ?? ''}
            onChange={(e) => onChange({ ...criterion, stage_key: e.target.value })}
          >
            <option value="">— select stage —</option>
            {stageKeys.map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
        )}

        {criterion.type === 'document_status' && (
          <div className="flex gap-1.5">
            <input
              className="flex-1 border border-border rounded px-2 py-1 text-xs bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="document type (e.g. FRS)"
              value={criterion.document_type ?? ''}
              onChange={(e) => onChange({ ...criterion, document_type: e.target.value })}
            />
            <select
              className="border border-border rounded px-2 py-1 text-xs bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              value={criterion.required_status ?? 'Approved'}
              onChange={(e) => onChange({ ...criterion, required_status: e.target.value })}
            >
              {DOCUMENT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        )}
      </div>

      <button
        onClick={onRemove}
        className="text-muted-foreground/40 hover:text-red-500 text-lg leading-none mt-0.5 shrink-0"
        title="Remove"
      >
        ×
      </button>
    </div>
  )
}

interface Props {
  criteria: CriterionDef[]
  stageKeys: string[]
  onChange: (updated: CriterionDef[]) => void
}

export default function RuleBuilder({ criteria, stageKeys, onChange }: Props) {
  const add = () => onChange([...criteria, { type: 'all_tasks_complete' }])

  const update = (i: number, updated: CriterionDef) => {
    const next = [...criteria]
    next[i] = updated
    onChange(next)
  }

  const remove = (i: number) => onChange(criteria.filter((_, idx) => idx !== i))

  return (
    <div>
      <div className="flex justify-end mb-1.5">
        <button onClick={add} className="text-xs text-primary hover:text-primary/80">+ Add</button>
      </div>
      {criteria.length === 0 && (
        <p className="text-xs text-muted-foreground/50 italic">None</p>
      )}
      <div className="space-y-1.5">
        {criteria.map((c, i) => (
          <CriterionRow
            key={i}
            criterion={c}
            stageKeys={stageKeys}
            onChange={(u) => update(i, u)}
            onRemove={() => remove(i)}
          />
        ))}
      </div>
    </div>
  )
}
