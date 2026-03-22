import CubeCellComponent, { EmptyCubeCell } from './CubeCell'
import CubeAxisLabels from './CubeAxisLabels'
import type { CubeCell, CubeLayout } from './useCubeData'
import type { HeatmapMode } from './colorUtils'
import { buildOwnerIndex } from './colorUtils'
import { useMemo } from 'react'
import { useAppStore } from '../../store'
import type { SliceFilters } from '../../types'

interface Props {
  layout: CubeLayout
  mode: HeatmapMode
}

export default function CubeGrid({ layout, mode }: Props) {
  const { setSliceFilters } = useAppStore()
  const { cells, xValues, yValues, zValues } = layout

  const occupiedKeys = useMemo(
    () => new Set(cells.map((c) => `${c.xIndex}:${c.yIndex}:${c.zIndex}`)),
    [cells],
  )

  const ownerIndex = useMemo(
    () => buildOwnerIndex(cells.flatMap((c) => c.owners)),
    [cells],
  )

  const handleCellClick = (cell: CubeCell) => {
    setSliceFilters(cell.dimValues as Partial<SliceFilters>)
  }

  return (
    <group>
      {/* Wireframe skeleton for empty slots */}
      {xValues.map((_, xi) =>
        yValues.map((_, yi) =>
          zValues.map((_, zi) => {
            const key = `${xi}:${yi}:${zi}`
            if (occupiedKeys.has(key)) return null
            return (
              <EmptyCubeCell
                key={key}
                xIndex={xi}
                yIndex={yi}
                zIndex={zi}
              />
            )
          })
        )
      )}

      {/* Occupied cells */}
      {cells.map((cell) => (
        <CubeCellComponent
          key={`${cell.xIndex}:${cell.yIndex}:${cell.zIndex}`}
          cell={cell}
          mode={mode}
          ownerIndex={ownerIndex}
          hasTimeHighlight={false}
          onClick={handleCellClick}
        />
      ))}

      <CubeAxisLabels layout={layout} />
    </group>
  )
}
