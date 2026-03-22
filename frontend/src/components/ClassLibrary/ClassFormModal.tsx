import { useState } from 'react'
import { useTemplates } from '../../hooks/useWorkflows'
import { useCreateClassDefinition, useUpdateClassDefinition } from '../../hooks/useClassDefinitions'
import type { ClassDefinition } from '../../types'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'

// Free-text suggestions — V3 generalises object_type
const OBJECT_TYPE_SUGGESTIONS = ['IO', 'CM', 'EM', 'Phase', 'Recipe', 'Unit_Procedure', 'Batch', 'PLC', 'HMI', 'SCADA', 'Motor', 'Valve', 'Pump', 'Other']

interface FormValues {
  name: string
  object_type: string
  description: string
  instance_count: string
  complexity: string
  workflow_template_id: string
}

function Field({ label, htmlFor, children }: { label: string; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label htmlFor={htmlFor} className="text-xs font-medium text-muted-foreground">{label}</Label>
      {children}
    </div>
  )
}

interface Props {
  mode: 'create' | 'edit'
  projectId: string
  initialValues?: ClassDefinition
  onClose: () => void
  onSuccess: (cls: ClassDefinition) => void
}

export default function ClassFormModal({ mode, projectId, initialValues, onClose, onSuccess }: Props) {
  const { data: templates = [] } = useTemplates()
  const createMutation = useCreateClassDefinition()
  const updateMutation = useUpdateClassDefinition()

  const [values, setValues] = useState<FormValues>({
    name: initialValues?.name ?? '',
    object_type: initialValues?.object_type ?? 'EM',
    description: initialValues?.description ?? '',
    instance_count: String(initialValues?.instance_count ?? 1),
    complexity: String(initialValues?.complexity ?? 1.0),
    workflow_template_id: initialValues?.workflow_template_id ?? '',
  })

  const setField = (field: keyof FormValues) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setValues((v) => ({ ...v, [field]: e.target.value }))

  const setSelect = (field: keyof FormValues) => (value: string) =>
    setValues((v) => ({ ...v, [field]: value }))

  const filteredTemplates = templates.filter(
    (t) => t.applies_to_type === values.object_type || t.applies_to_type === 'Other'
  )

  const isPending = createMutation.isPending || updateMutation.isPending
  const isError = createMutation.isError || updateMutation.isError

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!values.name.trim()) return

    const payload = {
      name: values.name.trim(),
      object_type: values.object_type,
      description: values.description.trim() || null,
      instance_count: Math.max(1, parseInt(values.instance_count) || 1),
      complexity: Math.max(0.1, parseFloat(values.complexity) || 1.0),
      workflow_template_id: values.workflow_template_id || null,
    }

    if (mode === 'create') {
      createMutation.mutate(
        { ...payload, project_id: projectId },
        { onSuccess: (cls) => { onSuccess(cls); onClose() } },
      )
    } else {
      updateMutation.mutate(
        { id: initialValues!.id, ...payload },
        { onSuccess: (cls) => { onSuccess(cls); onClose() } },
      )
    }
  }

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="max-w-md p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-5 py-4 border-b border-border">
          <DialogTitle className="text-sm font-semibold">
            {mode === 'create' ? 'New Class Definition' : 'Edit Class Definition'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col max-h-[75vh]">
          <div className="flex-1 overflow-auto px-5 py-4 space-y-4">
            <Field label="Name *" htmlFor="cls-name">
              <Input
                id="cls-name"
                className="h-8 text-sm"
                value={values.name}
                onChange={setField('name')}
                placeholder="e.g. Standard EM"
                required
                autoFocus
              />
            </Field>

            <Field label="Object Type" htmlFor="cls-type">
              <Input
                id="cls-type"
                className="h-8 text-sm"
                list="cls-type-list"
                value={values.object_type}
                onChange={setField('object_type')}
                placeholder="e.g. EM, PLC, Valve…"
              />
              <datalist id="cls-type-list">
                {OBJECT_TYPE_SUGGESTIONS.map((t) => <option key={t} value={t} />)}
              </datalist>
            </Field>

            <Field label="Workflow Template">
              <Select
                value={values.workflow_template_id || '_none'}
                onValueChange={(v) => setSelect('workflow_template_id')(v === '_none' ? '' : v)}
              >
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue placeholder="— none —" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none">— none —</SelectItem>
                  {filteredTemplates.map((t) => (
                    <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Instance Count" htmlFor="cls-count">
                <Input
                  id="cls-count"
                  type="number"
                  min={1}
                  className="h-8 text-sm"
                  value={values.instance_count}
                  onChange={setField('instance_count')}
                />
              </Field>
              <Field label="Complexity" htmlFor="cls-complexity">
                <Input
                  id="cls-complexity"
                  type="number"
                  min={0.1}
                  step={0.1}
                  className="h-8 text-sm"
                  value={values.complexity}
                  onChange={setField('complexity')}
                />
              </Field>
            </div>

            <Field label="Description" htmlFor="cls-desc">
              <textarea
                id="cls-desc"
                className="w-full border border-input bg-background rounded-md px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                rows={2}
                value={values.description}
                onChange={setField('description')}
                placeholder="Optional notes"
              />
            </Field>
          </div>

          <DialogFooter className="px-5 py-4 border-t border-border bg-muted/50 flex-row items-center">
            {isError && (
              <span className="text-xs text-destructive mr-auto">Save failed — check all fields.</span>
            )}
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isPending || !values.name.trim()}>
              {isPending ? 'Saving…' : mode === 'create' ? 'Create' : 'Save'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
