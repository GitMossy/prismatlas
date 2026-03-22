import { useAppStore } from '../../store'
import type { CubeLayout } from './useCubeData'
import type { SliceFilters } from '../../types'

const DIM_LABELS: Record<string, string> = {
  zone:        'Zone',
  stage:       'Stage',
  owner:       'Owner',
  object_type: 'Type',
}

interface Props {
  layout: CubeLayout
}

export default function CubeSliceNav({ layout }: Props) {
  const { sliceFilters, setSliceFilters } = useAppStore()
  const { zValues, zDim } = layout

  if (zValues.length === 0) return null

  const activeZ = (sliceFilters[zDim as keyof SliceFilters] as string | null) ?? null
  const activeIndex = activeZ !== null ? zValues.indexOf(activeZ) : -1
  const dimLabel = DIM_LABELS[zDim] ?? zDim

  const go = (delta: number) => {
    const newIndex =
      activeIndex === -1
        ? delta > 0 ? 0 : zValues.length - 1
        : (activeIndex + delta + zValues.length) % zValues.length
    setSliceFilters({ [zDim]: zValues[newIndex] } as Partial<SliceFilters>)
  }

  const clear = () => setSliceFilters({ [zDim]: null } as Partial<SliceFilters>)

  const displayLabel =
    activeZ !== null ? `${dimLabel}: ${activeZ.replace(/_/g, ' ')}` : 'All slices'
  const countLabel =
    activeZ !== null
      ? `${activeIndex + 1} / ${zValues.length}`
      : `${zValues.length} layers`

  return (
    <div className="flex items-center justify-center gap-3 px-5 py-2 bg-card/90 border-t border-border text-[13px] select-none">
      <button
        onClick={() => go(-1)}
        className="bg-muted border border-border rounded px-2.5 py-1 cursor-pointer text-sm text-foreground leading-none hover:bg-accent"
      >
        ◀
      </button>
      <span className="text-foreground">
        <strong>{displayLabel}</strong>
        <span className="text-muted-foreground ml-2">({countLabel})</span>
      </span>
      <button
        onClick={() => go(1)}
        className="bg-muted border border-border rounded px-2.5 py-1 cursor-pointer text-sm text-foreground leading-none hover:bg-accent"
      >
        ▶
      </button>
      {activeZ !== null && (
        <button
          onClick={clear}
          className="text-[11px] text-muted-foreground hover:text-foreground ml-1"
        >
          All
        </button>
      )}
    </div>
  )
}
