import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { TbCircleCheck, TbAlertCircle, TbArrowRight, TbLink } from 'react-icons/tb'
import { useAppStore } from '../../store'
import { useReadiness } from '../../hooks/useReadiness'
import { getObject, deleteObject } from '../../api/objects'
import { getDependencyRules } from '../../api/readiness'
import type { DependencyRuleDetail } from '../../api/readiness'
import ObjectFormModal from '../ObjectFormModal/ObjectFormModal'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog'
import type { Blocker, ProjectObject } from '../../types'

const BLOCKER_TYPE_ICON: Record<string, string> = {
  document: '📄',
  dependency: '🔗',
  task: '✅',
  stage_gate: '🚦',
  class: '📦',
}

function BlockerItem({ blocker, onNavigate }: { blocker: Blocker; onNavigate?: (id: string) => void }) {
  const icon = BLOCKER_TYPE_ICON[blocker.type] ?? '⚠️'
  const isBlocking = blocker.severity === 'blocking'
  return (
    <div className={`rounded p-2.5 text-xs ${
      isBlocking
        ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
        : 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800'
    }`}>
      <div className="flex items-start gap-1.5">
        <span className="shrink-0 mt-0.5">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className={`font-medium truncate ${isBlocking ? 'text-red-700 dark:text-red-400' : 'text-amber-700 dark:text-amber-400'}`}>
            {blocker.entity_name}
          </p>
          <p className="text-muted-foreground mt-0.5">{blocker.reason}</p>
        </div>
        {blocker.entity_id && onNavigate && blocker.type === 'dependency' && (
          <button
            onClick={() => onNavigate(blocker.entity_id!)}
            className="shrink-0 p-0.5 text-muted-foreground hover:text-primary rounded"
            title="Go to blocking object"
          >
            <TbArrowRight size={12} />
          </button>
        )}
      </div>
    </div>
  )
}

function CrossDependencies({ entityId, onNavigate }: { entityId: string; onNavigate: (id: string) => void }) {
  const { data: rules = [], isLoading } = useQuery<DependencyRuleDetail[]>({
    queryKey: ['dependency-rules', entityId],
    queryFn: () => getDependencyRules(entityId),
  })

  if (isLoading) return null
  if (rules.length === 0) return null

  const conditionLabel = (cond: Record<string, string>) => {
    if (cond.target_status) return `must be ${cond.target_status}`
    if (cond.target_stage_key) return `stage "${cond.target_stage_key}" complete`
    return 'condition met'
  }

  const statusColor = (status: string | null) => {
    if (status === 'complete') return 'text-green-600 dark:text-green-400'
    if (status === 'in_progress') return 'text-amber-600 dark:text-amber-400'
    return 'text-muted-foreground'
  }

  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
        <TbLink size={12} /> Cross-object dependencies ({rules.length})
      </p>
      <div className="space-y-1.5">
        {rules.map(rule => (
          <div
            key={rule.id}
            className={`rounded border p-2 text-xs flex items-start gap-2 ${
              rule.satisfied
                ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10'
                : 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10'
            }`}
          >
            {rule.satisfied
              ? <TbCircleCheck size={14} className="text-green-600 dark:text-green-400 shrink-0 mt-0.5" />
              : <TbAlertCircle size={14} className="text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
            }
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => onNavigate(rule.target_entity_id)}
                  className="font-medium text-foreground hover:text-primary truncate max-w-[140px] text-left"
                  title={`Go to ${rule.target_entity_name}`}
                >
                  {rule.target_entity_name}
                </button>
                <span className={`shrink-0 ${statusColor(rule.target_entity_status)}`}>
                  · {rule.target_entity_status ?? 'unknown'}
                </span>
              </div>
              <p className="text-muted-foreground mt-0.5">{conditionLabel(rule.condition)}</p>
              {!rule.satisfied && rule.reason && (
                <p className="text-red-600 dark:text-red-400 mt-0.5">{rule.reason}</p>
              )}
            </div>
            <button
              onClick={() => onNavigate(rule.target_entity_id)}
              className="shrink-0 p-0.5 text-muted-foreground hover:text-primary rounded"
              title="Go to this object"
            >
              <TbArrowRight size={12} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

function ReadinessDimension({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100)
  const colour = pct >= 90 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-500'
  return (
    <div>
      <div className="flex justify-between text-xs text-muted-foreground mb-1">
        <span>{label}</span>
        <span className="font-medium text-foreground">{pct}%</span>
      </div>
      <div className="bg-muted rounded-full h-1.5">
        <div className={`${colour} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function MetaRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex justify-between text-xs py-1 border-b border-border/50 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-foreground font-medium text-right max-w-[60%] truncate">{value || '—'}</span>
    </div>
  )
}

function ObjectDetail({ obj, onEdit, onDelete }: {
  obj: ProjectObject
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={onEdit} className="flex-1 text-xs h-8">
          Edit
        </Button>
        <Button variant="destructive" size="sm" onClick={onDelete} className="flex-1 text-xs h-8">
          Delete
        </Button>
      </div>

      <div className="bg-muted/50 rounded p-3">
        <MetaRow label="Type" value={obj.object_type} />
        <MetaRow label="Status" value={obj.status} />
        <MetaRow label="Zone" value={obj.zone} />
        <MetaRow label="Owner" value={obj.owner} />
        <MetaRow label="Planned Start" value={obj.planned_start} />
        <MetaRow label="Planned End" value={obj.planned_end} />
        {obj.description && <MetaRow label="Description" value={obj.description} />}
      </div>
    </div>
  )
}

export default function DetailPanel() {
  const { selectedProjectId, selectedEntity, setSelectedEntity } = useAppStore()
  const { data: readiness, isLoading, isError } = useReadiness(selectedEntity?.id ?? null)
  const queryClient = useQueryClient()

  const [showEditModal, setShowEditModal] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const { data: objectDetail } = useQuery<ProjectObject>({
    queryKey: ['object', selectedEntity?.id],
    queryFn: () => getObject(selectedEntity!.id),
    enabled: selectedEntity?.type === 'object',
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteObject(selectedEntity!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['objects'] })
      setSelectedEntity(null)
    },
  })

  if (!selectedEntity) return null

  const isObject = selectedEntity.type === 'object'

  return (
    <div className="w-80 bg-card border-l border-border flex flex-col h-full shrink-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="text-sm font-semibold text-card-foreground truncate pr-2">
          {objectDetail?.name ?? (selectedEntity.type === 'object' ? 'Object' : 'Document')}
        </span>
        <button
          onClick={() => setSelectedEntity(null)}
          className="text-muted-foreground hover:text-foreground text-lg leading-none shrink-0"
        >
          ×
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-5">
        {/* Object metadata + actions */}
        {isObject && objectDetail && (
          <ObjectDetail
            obj={objectDetail}
            onEdit={() => setShowEditModal(true)}
            onDelete={() => setConfirmDelete(true)}
          />
        )}

        {/* Readiness */}
        {isLoading && <p className="text-sm text-muted-foreground">Loading readiness…</p>}

        {isError && (
          <p className="text-sm text-amber-600 dark:text-amber-400">
            No readiness evaluation yet. Trigger one via <code className="text-xs bg-muted px-1 rounded">POST /entities/{'{id}'}/readiness/evaluate</code>.
          </p>
        )}

        {readiness && (
          <>
            {/* Overall */}
            <div className="text-center py-2">
              <p className="text-4xl font-bold text-foreground">
                {Math.round(readiness.overall_readiness * 100)}%
              </p>
              <p className="text-xs text-muted-foreground mt-1">overall readiness</p>
              <div className="flex justify-center gap-3 mt-2">
                <Badge variant={readiness.ready_for_fat ? 'ready' : 'secondary'}>
                  FAT {readiness.ready_for_fat ? '✓' : '—'}
                </Badge>
                <Badge variant={readiness.ready_for_sat ? 'ready' : 'secondary'}>
                  SAT {readiness.ready_for_sat ? '✓' : '—'}
                </Badge>
              </div>
            </div>

            {/* Dimensions */}
            <div className="space-y-3">
              <ReadinessDimension label="Technical" value={readiness.technical_readiness} />
              <ReadinessDimension label="Document" value={readiness.document_readiness} />
              <ReadinessDimension label="Stage / Dependencies" value={readiness.stage_readiness} />
            </div>

            {/* Next action */}
            {readiness.next_action && (
              <div className="bg-primary/10 border border-primary/20 rounded p-3">
                <p className="text-xs font-medium text-primary mb-0.5">Next action</p>
                <p className="text-xs text-primary/80">{readiness.next_action}</p>
              </div>
            )}

            {/* Blockers */}
            {readiness.blockers.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2">
                  Blockers ({readiness.blockers.length})
                </p>
                <div className="space-y-2">
                  {readiness.blockers.map((b, i) => (
                    <BlockerItem
                      key={i}
                      blocker={b}
                      onNavigate={(id) => setSelectedEntity({ id, type: 'object' })}
                    />
                  ))}
                </div>
              </div>
            )}

            {readiness.blockers.length === 0 && (
              <p className="text-xs text-green-600 dark:text-green-400 text-center">No blockers</p>
            )}

            {/* Cross-object dependencies */}
            {isObject && (
              <CrossDependencies
                entityId={selectedEntity.id}
                onNavigate={(id) => setSelectedEntity({ id, type: 'object' })}
              />
            )}
          </>
        )}
      </div>

      {/* Delete confirmation dialog */}
      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete "{objectDetail?.name}"?</DialogTitle>
            <DialogDescription>
              This will also remove its workflow instances and readiness evaluations. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit modal */}
      {showEditModal && objectDetail && selectedProjectId && (
        <ObjectFormModal
          mode="edit"
          projectId={selectedProjectId}
          initialValues={objectDetail}
          onClose={() => setShowEditModal(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['object', selectedEntity.id] })
          }}
        />
      )}
    </div>
  )
}
