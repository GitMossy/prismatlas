import { useMemo } from 'react'
import type { SliceResponse, SliceResultItem } from '../../types'
import type { CubeAxes, CubeAxisSort, CubeDimension } from '../../store'

export const STAGE_KEYS = [
  'engineering',
  'fat_prep',
  'fat_execution',
  'sat_prep',
  'sat_execution',
] as const

export type StageKey = (typeof STAGE_KEYS)[number]

export interface CubeCell {
  xIndex: number
  yIndex: number
  zIndex: number

  xVal: string
  yVal: string
  zVal: string

  // dimension → value mapping for setting slice filters on click
  dimValues: Partial<Record<CubeDimension, string>>

  count: number
  avgReadiness: number
  fatReadyCount: number
  satReadyCount: number
  blockerCount: number
  owners: string[]
}

export interface CubeLayout {
  cells: CubeCell[]
  xValues: string[]
  yValues: string[]
  zValues: string[]
  xDim: CubeDimension
  yDim: CubeDimension
  zDim: CubeDimension
}

function getDimValue(r: SliceResultItem, dim: CubeDimension): string {
  switch (dim) {
    case 'zone':        return r.zone ?? 'Unzoned'
    case 'stage':       return r.current_stage ?? 'engineering'
    case 'owner':       return r.owner ?? 'Unassigned'
    case 'object_type': return r.object_type ?? 'Unknown'
    default:            return dim  // hierarchy dimensions — used as label fallback
  }
}

function deriveValues(
  results: SliceResultItem[],
  dim: CubeDimension,
  dir: 'asc' | 'desc',
): string[] {
  let vals: string[]
  if (dim === 'stage') {
    const present = new Set(results.map((r) => getDimValue(r, 'stage')))
    vals = STAGE_KEYS.filter((k) => present.has(k)) as unknown as string[]
  } else {
    const set = new Set(results.map((r) => getDimValue(r, dim)))
    vals = [...set].sort()
  }
  return dir === 'desc' ? [...vals].reverse() : vals
}

export function useCubeData(
  data: SliceResponse | undefined,
  cubeAxes: CubeAxes,
  cubeAxisSort: CubeAxisSort,
): CubeLayout {
  return useMemo(() => {
    const empty: CubeLayout = {
      cells: [],
      xValues: [],
      yValues: [],
      zValues: [],
      xDim: cubeAxes.x,
      yDim: cubeAxes.y,
      zDim: cubeAxes.z,
    }
    if (!data || data.results.length === 0) return empty

    const { x: xDim, y: yDim, z: zDim } = cubeAxes

    const xValues = deriveValues(data.results, xDim, cubeAxisSort.x)
    const yValues = deriveValues(data.results, yDim, cubeAxisSort.y)
    const zValues = deriveValues(data.results, zDim, cubeAxisSort.z)

    type CellKey = string
    const cellMap = new Map<CellKey, {
      xi: number; yi: number; zi: number
      xVal: string; yVal: string; zVal: string
      items: SliceResultItem[]
    }>()

    for (const r of data.results) {
      const xVal = getDimValue(r, xDim)
      const yVal = getDimValue(r, yDim)
      const zVal = getDimValue(r, zDim)

      const xi = xValues.indexOf(xVal)
      const yi = yValues.indexOf(yVal)
      const zi = zValues.indexOf(zVal)

      if (xi === -1 || yi === -1 || zi === -1) continue

      const key: CellKey = `${xi}:${yi}:${zi}`
      if (!cellMap.has(key)) {
        cellMap.set(key, { xi, yi, zi, xVal, yVal, zVal, items: [] })
      }
      cellMap.get(key)!.items.push(r)
    }

    const cells: CubeCell[] = []
    for (const { xi, yi, zi, xVal, yVal, zVal, items } of cellMap.values()) {
      const count = items.length
      const avgReadiness = count > 0
        ? items.reduce((s, r) => s + r.overall_readiness, 0) / count
        : 0
      const fatReadyCount = items.filter((r) => r.ready_for_fat).length
      const satReadyCount = items.filter((r) => r.ready_for_sat).length
      const blockerCount  = items.reduce((s, r) => s + r.blocker_count, 0)
      const owners        = [...new Set(items.map((r) => r.owner).filter(Boolean) as string[])]

      cells.push({
        xIndex: xi, yIndex: yi, zIndex: zi,
        xVal, yVal, zVal,
        dimValues: { [xDim]: xVal, [yDim]: yVal, [zDim]: zVal } as Partial<Record<CubeDimension, string>>,
        count, avgReadiness, fatReadyCount, satReadyCount, blockerCount, owners,
      })
    }

    return { cells, xValues, yValues, zValues, xDim, yDim, zDim }
  }, [data, cubeAxes, cubeAxisSort])
}
