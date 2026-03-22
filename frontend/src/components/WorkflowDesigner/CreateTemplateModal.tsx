import { useState } from 'react'
import { useCreateTemplate } from '../../hooks/useWorkflows'

const OBJECT_TYPES = ['EM', 'IO', 'CM', 'Phase', 'Recipe', 'Unit_Procedure', 'document', 'Other']

interface Props {
  onClose: () => void
  onCreated: (id: string) => void
}

export default function CreateTemplateModal({ onClose, onCreated }: Props) {
  const [name, setName] = useState('')
  const [appliesTo, setAppliesTo] = useState('EM')
  const [description, setDescription] = useState('')
  const { mutate, isPending } = useCreateTemplate()

  const submit = () => {
    if (!name.trim()) return
    mutate(
      { name: name.trim(), applies_to_type: appliesTo, description: description || undefined },
      { onSuccess: (t) => onCreated(t.id) },
    )
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-lg shadow-xl w-96 p-6">
        <h2 className="text-base font-semibold text-foreground mb-4">New Workflow Template</h2>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Template name</label>
            <input
              autoFocus
              className="w-full border border-input bg-background rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="e.g. EM_Standard"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-1">Applies to</label>
            <select
              className="w-full border border-input bg-background rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              value={appliesTo}
              onChange={(e) => setAppliesTo(e.target.value)}
            >
              {OBJECT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-1">Description (optional)</label>
            <textarea
              className="w-full border border-input bg-background rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring resize-none"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={!name.trim() || isPending}
            className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
          >
            {isPending ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}
