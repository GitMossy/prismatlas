export type HeatmapMode = 'readiness' | 'time' | 'resource'

// Readiness palette — matches GraphView/Dashboard colours
const READINESS_GREEN = '#86efac'
const READINESS_AMBER = '#fcd34d'
const READINESS_RED = '#fca5a5'
const EMPTY_COLOR = '#e5e7eb'

// Up to 8 distinct owner colours
const OWNER_PALETTE = [
  '#60a5fa', '#f97316', '#a78bfa', '#34d399',
  '#fb7185', '#facc15', '#38bdf8', '#4ade80',
]

export function readinessColor(readiness: number): string {
  if (readiness >= 0.9) return READINESS_GREEN
  if (readiness >= 0.5) return READINESS_AMBER
  return READINESS_RED
}

export function emptyColor(): string {
  return EMPTY_COLOR
}

export function ownerColor(owner: string | null, ownerIndex: Map<string, number>): string {
  if (!owner) return EMPTY_COLOR
  const idx = ownerIndex.get(owner) ?? 0
  return OWNER_PALETTE[idx % OWNER_PALETTE.length]
}

export function buildOwnerIndex(owners: (string | null)[]): Map<string, number> {
  const unique = [...new Set(owners.filter(Boolean) as string[])]
  const map = new Map<string, number>()
  unique.forEach((o, i) => map.set(o, i))
  return map
}
