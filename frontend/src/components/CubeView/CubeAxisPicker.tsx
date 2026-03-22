import { useAppStore } from '../../store'
import type { CubeAxes, CubeDimension, SortDir } from '../../store'

const DIMENSIONS: { value: CubeDimension; label: string }[] = [
  { value: 'zone',        label: 'Zone' },
  { value: 'stage',       label: 'Stage' },
  { value: 'owner',       label: 'Owner' },
  { value: 'object_type', label: 'Object Type' },
]

export default function CubeAxisPicker() {
  const { cubeAxes, cubeAxisSort, setCubeAxes, setCubeAxisSort } = useAppStore()

  const handleDimChange = (axis: keyof CubeAxes, newDim: CubeDimension) => {
    setCubeAxes({ [axis]: newDim })
  }

  const toggleSort = (axis: keyof CubeAxes) => {
    const next: SortDir = cubeAxisSort[axis] === 'asc' ? 'desc' : 'asc'
    setCubeAxisSort({ [axis]: next })
  }

  return (
    <div className="absolute top-4 right-4 bg-card/90 backdrop-blur-sm border border-border rounded-lg p-3 text-[13px] z-10 min-w-[200px] shadow-sm">
      <div className="font-semibold mb-2.5 text-foreground tracking-wide">Pick 3 Axes</div>

      {(['x', 'y', 'z'] as const).map((axis) => (
        <div key={axis} className="flex items-center gap-1.5 mb-1.5">
          <span className="w-4 text-muted-foreground font-semibold text-xs uppercase shrink-0">
            {axis}
          </span>

          <select
            value={cubeAxes[axis]}
            onChange={(e) => handleDimChange(axis, e.target.value as CubeDimension)}
            className="flex-1 text-xs px-1.5 py-1 rounded border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
          >
            {DIMENSIONS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>

          <button
            title={cubeAxisSort[axis] === 'asc' ? 'Ascending — click to reverse' : 'Descending — click to restore'}
            onClick={() => toggleSort(axis)}
            className="bg-muted border border-border rounded px-1.5 py-1 cursor-pointer text-sm text-foreground leading-none shrink-0 hover:bg-accent"
          >
            {cubeAxisSort[axis] === 'asc' ? '↑' : '↓'}
          </button>
        </div>
      ))}
    </div>
  )
}
