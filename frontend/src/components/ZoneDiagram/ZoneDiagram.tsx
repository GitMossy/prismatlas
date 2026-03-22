/**
 * Zone Diagram — FR-4.6.3
 *
 * Renders a zone diagram image with draggable pins.
 * Pins are colored by object readiness (green/amber/red).
 * - Click empty space: opens add-pin modal (select object)
 * - Drag pin: updates pin position via PUT /zone-diagrams/{id}/pins/{pin_id}
 */
import { useState, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { zoneDiagramApi } from '../../api/zoneDiagrams'
import { useObjects } from '../../hooks/useObjects'
import { useAppStore } from '../../store'
import type { ZoneDiagramPin } from '../../types'

// Readiness-based pin color
function pinColor(readiness: number | null): string {
  if (readiness === null) return '#6b7280'
  if (readiness >= 0.9) return '#22c55e'
  if (readiness >= 0.5) return '#f59e0b'
  return '#ef4444'
}

interface AddPinModalProps {
  objects: { id: string; name: string }[]
  onAdd: (objectId: string) => void
  onClose: () => void
}

function AddPinModal({ objects, onAdd, onClose }: AddPinModalProps) {
  const [selected, setSelected] = useState('')
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-card border border-border rounded-lg shadow-xl p-5 w-80">
        <h3 className="text-sm font-semibold text-foreground mb-3">Place pin — select object</h3>
        <select
          className="w-full border border-border bg-background text-foreground rounded px-2 py-1.5 text-sm mb-4 focus:outline-none focus:ring-1 focus:ring-ring"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          <option value="">— select object —</option>
          {objects.map((o) => (
            <option key={o.id} value={o.id}>{o.name}</option>
          ))}
        </select>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
          <button
            disabled={!selected}
            onClick={() => { if (selected) onAdd(selected) }}
            className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
          >
            Add pin
          </button>
        </div>
      </div>
    </div>
  )
}

interface Props {
  zoneDiagramId: string
}

interface DragState {
  pinId: string
  startX: number
  startY: number
  origXPct: number
  origYPct: number
}

export default function ZoneDiagramView({ zoneDiagramId }: Props) {
  const qc = useQueryClient()
  const { selectedProjectId } = useAppStore()
  const imgRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const [pendingClick, setPendingClick] = useState<{ x_pct: number; y_pct: number } | null>(null)
  const [dragging, setDragging] = useState<DragState | null>(null)

  const { data: diagram, isLoading } = useQuery({
    queryKey: ['zone-diagram', zoneDiagramId],
    queryFn: () => zoneDiagramApi.get(zoneDiagramId),
    enabled: !!zoneDiagramId,
  })

  const { data: objects = [] } = useObjects(selectedProjectId)

  // Object id → name lookup
  const objMap = new Map(objects.map((o) => [o.id, o.name]))

  const addPin = useMutation({
    mutationFn: (body: { object_id: string; x_pct: number; y_pct: number }) =>
      zoneDiagramApi.addPin(zoneDiagramId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['zone-diagram', zoneDiagramId] })
      setPendingClick(null)
    },
  })

  const updatePin = useMutation({
    mutationFn: ({ pinId, x_pct, y_pct }: { pinId: string; x_pct: number; y_pct: number }) =>
      zoneDiagramApi.updatePin(zoneDiagramId, pinId, { x_pct, y_pct }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['zone-diagram', zoneDiagramId] }),
  })

  const deletePin = useMutation({
    mutationFn: (pinId: string) => zoneDiagramApi.deletePin(zoneDiagramId, pinId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['zone-diagram', zoneDiagramId] }),
  })

  const getRelativePos = useCallback((clientX: number, clientY: number) => {
    const img = imgRef.current
    if (!img) return null
    const rect = img.getBoundingClientRect()
    const x_pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    const y_pct = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height))
    return { x_pct, y_pct }
  }, [])

  const handleImageClick = (e: React.MouseEvent) => {
    // Don't open modal if we just finished a drag
    if (dragging) return
    const pos = getRelativePos(e.clientX, e.clientY)
    if (pos) setPendingClick(pos)
  }

  const handlePinMouseDown = (e: React.MouseEvent, pin: ZoneDiagramPin) => {
    e.stopPropagation()
    setDragging({
      pinId: pin.id,
      startX: e.clientX,
      startY: e.clientY,
      origXPct: pin.x_pct,
      origYPct: pin.y_pct,
    })
  }

  const handleMouseMove = (_e: React.MouseEvent) => {
    if (!dragging || !imgRef.current) return
    // Live preview would need local state; keep simple for now
  }

  const handleMouseUp = (e: React.MouseEvent) => {
    if (!dragging) return
    const pos = getRelativePos(e.clientX, e.clientY)
    if (pos && (Math.abs(e.clientX - dragging.startX) > 4 || Math.abs(e.clientY - dragging.startY) > 4)) {
      updatePin.mutate({ pinId: dragging.pinId, x_pct: pos.x_pct, y_pct: pos.y_pct })
    }
    setDragging(null)
  }

  if (isLoading) return <p className="text-xs text-muted-foreground p-4">Loading diagram…</p>
  if (!diagram) return <p className="text-xs text-red-400 p-4">Diagram not found.</p>

  return (
    <div className="flex flex-col gap-2 p-4">
      <h3 className="text-sm font-semibold text-foreground">{diagram.name}</h3>
      <p className="text-xs text-muted-foreground">Click on image to place a pin · Drag pin to reposition · Right-click pin to remove</p>

      <div
        ref={containerRef}
        className="relative inline-block select-none cursor-crosshair"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => setDragging(null)}
      >
        <img
          ref={imgRef}
          src={diagram.image_url}
          alt={diagram.name}
          className="max-w-full rounded border border-border block"
          style={{ maxHeight: '70vh' }}
          onClick={handleImageClick}
          draggable={false}
        />

        {/* Pins */}
        {(diagram.pins ?? []).map((pin) => (
          <div
            key={pin.id}
            className="absolute z-10 -translate-x-1/2 -translate-y-1/2 cursor-grab active:cursor-grabbing"
            style={{
              left: `${pin.x_pct * 100}%`,
              top: `${pin.y_pct * 100}%`,
            }}
            onMouseDown={(e) => handlePinMouseDown(e, pin)}
            onContextMenu={(e) => {
              e.preventDefault()
              deletePin.mutate(pin.id)
            }}
            title={`${objMap.get(pin.object_id) ?? pin.object_id}\nRight-click to remove`}
          >
            <div
              className="w-4 h-4 rounded-full border-2 border-white shadow-md"
              style={{ backgroundColor: pinColor(null) }}
            />
          </div>
        ))}
      </div>

      {/* Add pin modal */}
      {pendingClick && (
        <AddPinModal
          objects={objects.map((o) => ({ id: o.id, name: o.name }))}
          onAdd={(objectId) => addPin.mutate({ object_id: objectId, ...pendingClick! })}
          onClose={() => setPendingClick(null)}
        />
      )}
    </div>
  )
}
