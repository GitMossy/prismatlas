/**
 * ObjectFormModal — used for both Create and Edit.
 * Uses shadcn Dialog for proper focus trap and ESC close.
 */
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createObject, updateObject } from '../../api/objects'
import client from '../../api/client'
import type { ProjectObject, Area, Unit } from '../../types'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'

// Object types are free-text (V3 generalisation). These are common suggestions only.
const OBJECT_TYPE_SUGGESTIONS = ['IO', 'CM', 'EM', 'Phase', 'Recipe', 'Unit_Procedure', 'Batch', 'PLC', 'HMI', 'SCADA', 'Motor', 'Valve', 'Pump', 'Other']
const STATUSES = ['not_started', 'in_progress', 'blocked', 'complete']
const STATUS_LABELS: Record<string, string> = {
  not_started: 'Not Started',
  in_progress: 'In Progress',
  blocked:     'Blocked',
  complete:    'Complete',
}

interface FormValues {
  name: string
  object_type: string
  status: string
  description: string
  zone: string
  owner: string
  planned_start: string
  planned_end: string
  area_id: string
  unit_id: string
}

const EMPTY: FormValues = {
  name: '',
  object_type: 'EM',
  status: 'not_started',
  description: '',
  zone: '',
  owner: '',
  planned_start: '',
  planned_end: '',
  area_id: '',
  unit_id: '',
}

interface Props {
  mode: 'create' | 'edit'
  projectId: string
  initialValues?: Partial<ProjectObject>
  onClose: () => void
  onSuccess: (obj: ProjectObject) => void
}

function useAreas(projectId: string) {
  return useQuery<Area[]>({
    queryKey: ['areas', projectId],
    queryFn: () => client.get('/areas', { params: { project_id: projectId } }).then((r) => r.data),
    enabled: !!projectId,
  })
}

function useUnitsForArea(areaId: string) {
  return useQuery<Unit[]>({
    queryKey: ['units', areaId],
    queryFn: () => client.get('/units', { params: { area_id: areaId } }).then((r) => r.data),
    enabled: !!areaId,
  })
}

function Field({ label, htmlFor, children }: { label: string; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label htmlFor={htmlFor} className="text-xs font-medium text-muted-foreground">{label}</Label>
      {children}
    </div>
  )
}

export default function ObjectFormModal({ mode, projectId, initialValues, onClose, onSuccess }: Props) {
  const queryClient = useQueryClient()

  const [values, setValues] = useState<FormValues>(() => ({
    ...EMPTY,
    name: initialValues?.name ?? '',
    object_type: initialValues?.object_type ?? 'EM',
    status: initialValues?.status ?? 'not_started',
    description: initialValues?.description ?? '',
    zone: initialValues?.zone ?? '',
    owner: initialValues?.owner ?? '',
    planned_start: initialValues?.planned_start ?? '',
    planned_end: initialValues?.planned_end ?? '',
    area_id: initialValues?.area_id ?? '',
    unit_id: initialValues?.unit_id ?? '',
  }))

  const { data: areas = [] } = useAreas(projectId)
  const { data: units = [] } = useUnitsForArea(values.area_id)

  useEffect(() => {
    const unitBelongsToArea = units.some((u) => u.id === values.unit_id)
    if (values.unit_id && !unitBelongsToArea) {
      setValues((v) => ({ ...v, unit_id: '' }))
    }
  }, [units, values.unit_id])

  const setField = (field: keyof FormValues) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setValues((v) => ({ ...v, [field]: e.target.value }))

  const setSelect = (field: keyof FormValues) => (value: string) =>
    setValues((v) => ({ ...v, [field]: value }))

  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        name: values.name.trim(),
        object_type: values.object_type,
        status: values.status,
        description: values.description.trim() || null,
        zone: values.zone.trim() || null,
        owner: values.owner.trim() || null,
        planned_start: values.planned_start || null,
        planned_end: values.planned_end || null,
        area_id: values.area_id || null,
        unit_id: values.unit_id || null,
      }
      if (mode === 'create') {
        return createObject({ ...payload, project_id: projectId })
      } else {
        return updateObject(initialValues!.id!, payload)
      }
    },
    onSuccess: (obj) => {
      queryClient.invalidateQueries({ queryKey: ['objects'] })
      onSuccess(obj)
      onClose()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!values.name.trim()) return
    mutation.mutate()
  }

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="max-w-md p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-5 py-4 border-b border-border">
          <DialogTitle className="text-sm font-semibold">
            {mode === 'create' ? 'New Object' : 'Edit Object'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col max-h-[75vh]">
          <div className="flex-1 overflow-auto px-5 py-4 space-y-4">
            <Field label="Name *" htmlFor="obj-name">
              <Input
                id="obj-name"
                className="h-8 text-sm"
                value={values.name}
                onChange={setField('name')}
                placeholder="e.g. FIC-101"
                required
                autoFocus
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Type" htmlFor="obj-type">
                {/* Free-text input with suggestions — V3 generalises object_type beyond DeltaV */}
                <Input
                  id="obj-type"
                  className="h-8 text-sm"
                  list="obj-type-list"
                  value={values.object_type}
                  onChange={setField('object_type')}
                  placeholder="e.g. EM, PLC, Valve…"
                />
                <datalist id="obj-type-list">
                  {OBJECT_TYPE_SUGGESTIONS.map((t) => <option key={t} value={t} />)}
                </datalist>
              </Field>

              <Field label="Status">
                <Select value={values.status} onValueChange={setSelect('status')}>
                  <SelectTrigger className="h-8 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUSES.map((s) => <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Area">
                <Select
                  value={values.area_id || '_none'}
                  onValueChange={(v) => setSelect('area_id')(v === '_none' ? '' : v)}
                >
                  <SelectTrigger className="h-8 text-sm">
                    <SelectValue placeholder="— none —" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_none">— none —</SelectItem>
                    {areas.map((a) => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>

              <Field label="Unit">
                <Select
                  value={values.unit_id || '_none'}
                  onValueChange={(v) => setSelect('unit_id')(v === '_none' ? '' : v)}
                  disabled={!values.area_id}
                >
                  <SelectTrigger className="h-8 text-sm">
                    <SelectValue placeholder="— none —" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_none">— none —</SelectItem>
                    {units.map((u) => <SelectItem key={u.id} value={u.id}>{u.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Zone" htmlFor="obj-zone">
                <Input id="obj-zone" className="h-8 text-sm" value={values.zone} onChange={setField('zone')} placeholder="e.g. Zone A" />
              </Field>
              <Field label="Owner" htmlFor="obj-owner">
                <Input id="obj-owner" className="h-8 text-sm" value={values.owner} onChange={setField('owner')} placeholder="e.g. J. Smith" />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Planned Start" htmlFor="obj-start">
                <Input id="obj-start" type="date" className="h-8 text-sm" value={values.planned_start} onChange={setField('planned_start')} />
              </Field>
              <Field label="Planned End" htmlFor="obj-end">
                <Input id="obj-end" type="date" className="h-8 text-sm" value={values.planned_end} onChange={setField('planned_end')} />
              </Field>
            </div>

            <Field label="Description" htmlFor="obj-desc">
              <textarea
                id="obj-desc"
                className="w-full border border-input bg-background rounded-md px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                rows={2}
                value={values.description}
                onChange={setField('description')}
                placeholder="Optional notes"
              />
            </Field>
          </div>

          <DialogFooter className="px-5 py-4 border-t border-border bg-muted/50 flex-row items-center">
            {mutation.isError && (
              <span className="text-xs text-destructive mr-auto">Save failed — check all fields.</span>
            )}
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={mutation.isPending || !values.name.trim()}>
              {mutation.isPending ? 'Saving…' : mode === 'create' ? 'Create' : 'Save'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
