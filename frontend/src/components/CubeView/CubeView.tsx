import { useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'

import { useAppStore } from '../../store'
import { useSliceQuery } from '../../hooks/useSlice'
import { useCubeData } from './useCubeData'
import CubeGrid from './CubeGrid'
import CubeLegend from './CubeLegend'
import CubeAxisPicker from './CubeAxisPicker'
import CubeSliceNav from './CubeSliceNav'
import type { HeatmapMode } from './colorUtils'

export default function CubeView() {
  const { selectedProjectId, sliceFilters, cubeAxes, cubeAxisSort } = useAppStore()
  const [heatmapMode, setHeatmapMode] = useState<HeatmapMode>('readiness')

  const { data, isLoading } = useSliceQuery(selectedProjectId, sliceFilters)
  const layout = useCubeData(data, cubeAxes, cubeAxisSort)

  if (!selectedProjectId) return null

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Loading cube data…
      </div>
    )
  }

  if (layout.cells.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        No data to display. Apply filters or add objects with zone and stage data.
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col" style={{ minHeight: 0 }}>
      <div className="relative flex-1" style={{ minHeight: 0 }}>
        <Canvas
          style={{ width: '100%', height: '100%' }}
          camera={{ position: [8, 8, 12], fov: 45 }}
        >
          <ambientLight intensity={0.6} />
          <directionalLight position={[10, 10, 5]} intensity={0.8} />
          <OrbitControls makeDefault />
          <CubeGrid layout={layout} mode={heatmapMode} />
        </Canvas>

        <CubeLegend
          mode={heatmapMode}
          onModeChange={setHeatmapMode}
          cellCount={layout.cells.length}
        />

        <CubeAxisPicker />
      </div>

      <CubeSliceNav layout={layout} />
    </div>
  )
}
