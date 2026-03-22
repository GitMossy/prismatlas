import { Billboard, Text } from '@react-three/drei'
import { STEP } from './CubeCell'
import type { CubeLayout } from './useCubeData'

const DIM_LABELS: Record<string, string> = {
  zone:        'Zone',
  stage:       'Stage',
  owner:       'Owner',
  object_type: 'Type',
}

interface Props {
  layout: CubeLayout
}

export default function CubeAxisLabels({ layout }: Props) {
  const { xValues, yValues, zValues, xDim, yDim, zDim } = layout

  return (
    <group>
      {/* ── X axis ── */}
      <Billboard position={[((xValues.length - 1) * STEP) / 2, -2, 0]}>
        <Text fontSize={0.22} color="#6b7280" anchorX="center" anchorY="middle">
          {DIM_LABELS[xDim] ?? xDim}
        </Text>
      </Billboard>

      {xValues.map((val, i) => (
        <Billboard key={`x-${i}`} position={[i * STEP, -1.3, 0]}>
          <Text fontSize={0.22} color="#374151" anchorX="center" anchorY="middle">
            {val.replace(/_/g, ' ')}
          </Text>
        </Billboard>
      ))}

      {/* ── Y axis ── */}
      <Billboard position={[-2.2, ((yValues.length - 1) * STEP) / 2, 0]}>
        <Text fontSize={0.22} color="#6b7280" anchorX="center" anchorY="middle">
          {DIM_LABELS[yDim] ?? yDim}
        </Text>
      </Billboard>

      {yValues.map((val, i) => (
        <Billboard key={`y-${i}`} position={[-1.5, i * STEP, 0]}>
          <Text fontSize={0.22} color="#374151" anchorX="center" anchorY="middle">
            {val.replace(/_/g, ' ')}
          </Text>
        </Billboard>
      ))}

      {/* ── Z axis ── */}
      <Billboard position={[0, -2, ((zValues.length - 1) * STEP) / 2]}>
        <Text fontSize={0.22} color="#6b7280" anchorX="center" anchorY="middle">
          {DIM_LABELS[zDim] ?? zDim}
        </Text>
      </Billboard>

      {zValues.map((val, i) => (
        <Billboard key={`z-${i}`} position={[0, -1.3, i * STEP]}>
          <Text fontSize={0.22} color="#374151" anchorX="center" anchorY="middle">
            {val.replace(/_/g, ' ')}
          </Text>
        </Billboard>
      ))}
    </group>
  )
}
