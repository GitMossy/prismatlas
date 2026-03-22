import { useRef, useState } from 'react'
import { type ThreeEvent } from '@react-three/fiber'
import type { Mesh } from 'three'
import type { CubeCell as CubeCellData } from './useCubeData'
import type { HeatmapMode } from './colorUtils'
import { readinessColor, ownerColor } from './colorUtils'

const CELL_SIZE = 1
const CELL_GAP = 0.15
const STEP = CELL_SIZE + CELL_GAP

interface Props {
  cell: CubeCellData
  mode: HeatmapMode
  ownerIndex: Map<string, number>
  hasTimeHighlight: boolean
  onClick: (cell: CubeCellData) => void
}

export default function CubeCell({ cell, mode, ownerIndex, hasTimeHighlight, onClick }: Props) {
  const meshRef = useRef<Mesh>(null)
  const [hovered, setHovered] = useState(false)

  const x = cell.xIndex * STEP
  const y = cell.yIndex * STEP
  const z = cell.zIndex * STEP

  let color: string
  if (mode === 'readiness') {
    color = readinessColor(cell.avgReadiness)
  } else if (mode === 'time') {
    color = hasTimeHighlight ? '#60a5fa' : '#e5e7eb'
  } else {
    color = ownerColor(cell.owners[0] ?? null, ownerIndex)
  }

  const opacity = hovered ? 0.9 : 0.75

  return (
    <mesh
      ref={meshRef}
      position={[x, y, z]}
      onClick={(e: ThreeEvent<MouseEvent>) => { e.stopPropagation(); onClick(cell) }}
      onPointerOver={(e: ThreeEvent<PointerEvent>) => { e.stopPropagation(); setHovered(true) }}
      onPointerOut={() => setHovered(false)}
    >
      <boxGeometry args={[CELL_SIZE, CELL_SIZE, CELL_SIZE]} />
      <meshStandardMaterial color={color} transparent opacity={opacity} />
    </mesh>
  )
}

// Wireframe placeholder for empty cells
export function EmptyCubeCell({ xIndex, yIndex, zIndex }: {
  xIndex: number
  yIndex: number
  zIndex: number
}) {
  const x = xIndex * STEP
  const y = yIndex * STEP
  const z = zIndex * STEP

  return (
    <mesh position={[x, y, z]}>
      <boxGeometry args={[CELL_SIZE, CELL_SIZE, CELL_SIZE]} />
      <meshStandardMaterial color="#d1d5db" transparent opacity={0.08} wireframe />
    </mesh>
  )
}

export { STEP }
