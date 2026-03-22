import type { HeatmapMode } from './colorUtils'

interface LegendProps {
  mode: HeatmapMode
  onModeChange: (mode: HeatmapMode) => void
  cellCount: number
}

const MODES: { value: HeatmapMode; label: string }[] = [
  { value: 'readiness', label: 'Readiness' },
  { value: 'time', label: 'Time' },
  { value: 'resource', label: 'Resource' },
]

const READINESS_LEGEND = [
  { color: '#86efac', label: '≥ 90%' },
  { color: '#fcd34d', label: '50–90%' },
  { color: '#fca5a5', label: '< 50%' },
  { color: '#e5e7eb', label: 'Empty' },
]

export default function CubeLegend({ mode, onModeChange, cellCount }: LegendProps) {
  return (
    <div className="absolute bottom-4 left-4 bg-card/90 backdrop-blur-sm border border-border rounded-lg shadow p-3 text-xs min-w-[160px]">
      <p className="font-semibold text-foreground mb-2">Heatmap</p>

      {/* Mode toggle */}
      <div className="flex gap-1 mb-3">
        {MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => onModeChange(m.value)}
            className={`flex-1 px-1.5 py-1 rounded text-[10px] font-medium transition-colors
              ${mode === m.value
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-accent'
              }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Colour key */}
      {mode === 'readiness' && (
        <div className="space-y-1">
          {READINESS_LEGEND.map((l) => (
            <div key={l.label} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm shrink-0" style={{ background: l.color }} />
              <span className="text-muted-foreground">{l.label}</span>
            </div>
          ))}
        </div>
      )}
      {mode === 'time' && (
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm bg-primary/60" />
          <span className="text-muted-foreground">In date range</span>
        </div>
      )}
      {mode === 'resource' && (
        <span className="text-muted-foreground">Coloured by owner</span>
      )}

      <p className="text-muted-foreground/60 mt-2">{cellCount} occupied cells</p>
    </div>
  )
}
