import { useEffect, useState } from 'react'
import { DndContext, closestCenter, type DragEndEvent } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable'
import { useTemplateVersions, useCreateTemplateVersion } from '../../hooks/useWorkflows'
import type { WorkflowTemplate, WorkflowTemplateVersion, TemplateDef, StageDef } from '../../types'
import StageCard from './StageCard'
import SimulationPanel from './SimulationPanel'
import FlowEditor from './FlowEditor'

const EMPTY_DEF: TemplateDef = { stages: [] }

interface Props {
  template: WorkflowTemplate
  selectedVersionId: string | null
}

export default function TemplateEditor({ template, selectedVersionId }: Props) {
  const { data: versions = [] } = useTemplateVersions(template.id)
  const { mutate: saveVersion, isPending: isSaving } = useCreateTemplateVersion(template.id)

  const [definition, setDefinition] = useState<TemplateDef>(EMPTY_DEF)
  const [tab, setTab] = useState<'stages' | 'simulate' | 'flow'>('stages')
  const [dirty, setDirty] = useState(false)
  const [savedMsg, setSavedMsg] = useState('')

  // Load selected version's definition into editor
  useEffect(() => {
    if (!selectedVersionId) {
      setDefinition(EMPTY_DEF)
      setDirty(false)
      return
    }
    const version = versions.find((v: WorkflowTemplateVersion) => v.id === selectedVersionId)
    if (version) {
      setDefinition(version.definition)
      setDirty(false)
    }
  }, [selectedVersionId, versions])

  const updateDef = (next: TemplateDef) => {
    setDefinition(next)
    setDirty(true)
    setSavedMsg('')
  }

  const addStage = () => {
    const key = `stage_${Date.now()}`
    const next: StageDef = {
      key,
      name: '',
      order: definition.stages.length + 1,
      is_mandatory: true,
      entry_criteria: [],
      exit_criteria: [{ type: 'all_tasks_complete' }],
      tasks: [],
    }
    updateDef({ stages: [...definition.stages, next] })
  }

  const updateStage = (i: number, updated: StageDef) => {
    const stages = [...definition.stages]
    stages[i] = updated
    updateDef({ stages })
  }

  const removeStage = (i: number) => {
    updateDef({ stages: definition.stages.filter((_, idx) => idx !== i) })
  }

  const handleStageDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIdx = definition.stages.findIndex((s) => s.key === active.id)
    const newIdx = definition.stages.findIndex((s) => s.key === over.id)
    const reordered = arrayMove(definition.stages, oldIdx, newIdx).map((s, i) => ({ ...s, order: i + 1 }))
    updateDef({ stages: reordered })
  }

  const save = () => {
    saveVersion(definition, {
      onSuccess: () => {
        setDirty(false)
        setSavedMsg('Saved as new version')
        setTimeout(() => setSavedMsg(''), 3000)
      },
    })
  }

  const allStageKeys = definition.stages.map((s) => s.key)

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Editor header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card shrink-0">
        <div>
          <p className="text-sm font-semibold text-foreground">{template.name}</p>
          <p className="text-xs text-muted-foreground">
            {template.applies_to_type} ·{' '}
            {selectedVersionId
              ? `v${versions.find((v: WorkflowTemplateVersion) => v.id === selectedVersionId)?.version_number ?? '?'}`
              : 'no version selected'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {savedMsg && <span className="text-xs text-green-600">{savedMsg}</span>}
          {dirty && <span className="text-xs text-amber-500">Unsaved changes</span>}
          <button
            onClick={save}
            disabled={isSaving || !dirty}
            className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isSaving ? 'Saving…' : 'Save as new version'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 px-5 pt-3 bg-card border-b border-border shrink-0">
        {(['stages', 'flow', 'simulate'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 text-sm capitalize border-b-2 transition-colors ${
              tab === t ? 'border-primary text-primary font-medium' : 'border-transparent text-muted-foreground'
            }`}
          >
            {t === 'stages' ? 'Stages & Tasks' : t === 'flow' ? 'Flow Diagram' : 'Simulation'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className={`flex-1 bg-muted/30 ${tab === 'flow' ? 'overflow-hidden flex flex-col' : 'overflow-auto p-5'}`}>
        {tab === 'stages' && (
          <div className="max-w-2xl space-y-3">
            <DndContext collisionDetection={closestCenter} onDragEnd={handleStageDragEnd}>
              <SortableContext
                items={definition.stages.map((s) => s.key)}
                strategy={verticalListSortingStrategy}
              >
                {definition.stages.map((stage, i) => (
                  <StageCard
                    key={stage.key}
                    stage={stage}
                    allStageKeys={allStageKeys}
                    onChange={(updated) => updateStage(i, updated)}
                    onRemove={() => removeStage(i)}
                  />
                ))}
              </SortableContext>
            </DndContext>

            <button
              onClick={addStage}
              className="w-full py-2.5 border-2 border-dashed border-border rounded-lg text-sm text-muted-foreground hover:border-primary hover:text-primary transition-colors"
            >
              + Add stage
            </button>

            {definition.stages.length === 0 && (
              <p className="text-center text-muted-foreground text-sm py-8">
                No stages yet. Add a stage to get started.
              </p>
            )}
          </div>
        )}

        {tab === 'flow' && (
          <FlowEditor definition={definition} onChange={updateDef} />
        )}

        {tab === 'simulate' && (
          <div className="max-w-lg">
            <SimulationPanel definition={definition} />
          </div>
        )}
      </div>
    </div>
  )
}
