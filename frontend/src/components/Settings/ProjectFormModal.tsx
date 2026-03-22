import { useState } from 'react'
import { useCreateProject, useUpdateProject } from '../../hooks/useProjects'
import type { Project } from '../../types'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'

interface Props {
  mode: 'create' | 'edit'
  initial?: Project
  onClose: () => void
  onSuccess?: (p: Project) => void
}

export default function ProjectFormModal({ mode, initial, onClose, onSuccess }: Props) {
  const [name, setName] = useState(initial?.name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')

  const create = useCreateProject()
  const update = useUpdateProject()

  const isPending = create.isPending || update.isPending
  const isError   = create.isError   || update.isError

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    const payload = { name: name.trim(), description: description.trim() || undefined }

    if (mode === 'create') {
      create.mutate(payload, {
        onSuccess: (p) => { onSuccess?.(p); onClose() },
      })
    } else {
      update.mutate({ id: initial!.id, ...payload }, {
        onSuccess: (p) => { onSuccess?.(p); onClose() },
      })
    }
  }

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-sm p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-5 py-4 border-b border-border">
          <DialogTitle className="text-sm font-semibold">
            {mode === 'create' ? 'New Project' : 'Edit Project'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="px-5 py-4 space-y-3">
            <div className="space-y-1">
              <Label htmlFor="proj-name" className="text-xs text-muted-foreground">Name *</Label>
              <Input
                id="proj-name"
                className="h-8 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Distillation Unit Upgrade"
                required
                autoFocus
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="proj-desc" className="text-xs text-muted-foreground">Description</Label>
              <textarea
                id="proj-desc"
                className="w-full border border-input bg-background rounded-md px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>

          <DialogFooter className="px-5 py-3 border-t border-border bg-muted/50 flex-row items-center">
            {isError && (
              <span className="text-xs text-destructive mr-auto">Save failed.</span>
            )}
            <Button type="button" variant="outline" size="sm" onClick={onClose}>Cancel</Button>
            <Button type="submit" size="sm" disabled={isPending || !name.trim()}>
              {isPending ? 'Saving…' : mode === 'create' ? 'Create' : 'Save'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
