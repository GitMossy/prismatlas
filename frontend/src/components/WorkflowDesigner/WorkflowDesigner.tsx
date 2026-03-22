import { useState } from 'react'
import { useTemplate, useTemplateVersions } from '../../hooks/useWorkflows'
import TemplateLibrary from './TemplateLibrary'
import TemplateEditor from './TemplateEditor'
import CreateTemplateModal from './CreateTemplateModal'
import EditTemplateModal from './EditTemplateModal'
import type { WorkflowTemplate } from '../../types'

export default function WorkflowDesigner() {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<WorkflowTemplate | null>(null)

  const { data: template } = useTemplate(selectedTemplateId)
  const { data: versions = [] } = useTemplateVersions(selectedTemplateId)

  const handleSelectTemplate = (id: string) => {
    setSelectedTemplateId(id)
    setSelectedVersionId(null)
  }

  const handleSelectVersion = (versionId: string) => {
    setSelectedVersionId(versionId)
  }

  const handleCreated = (id: string) => {
    setShowCreate(false)
    setSelectedTemplateId(id)
    setSelectedVersionId(null)
  }

  const handleDeleted = (id: string) => {
    if (selectedTemplateId === id) {
      setSelectedTemplateId(null)
      setSelectedVersionId(null)
    }
  }

  // Auto-select latest version when template is selected and no version chosen
  if (selectedTemplateId && !selectedVersionId && versions.length > 0) {
    setSelectedVersionId(versions[0].id)
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      <TemplateLibrary
        selectedTemplateId={selectedTemplateId}
        selectedVersionId={selectedVersionId}
        onSelectTemplate={handleSelectTemplate}
        onSelectVersion={handleSelectVersion}
        onCreateTemplate={() => setShowCreate(true)}
        onEditTemplate={setEditingTemplate}
        onDeletedTemplate={handleDeleted}
        onVersionDeleted={(_templateId, deletedVersionId) => {
          if (selectedVersionId === deletedVersionId) {
            setSelectedVersionId(null)
          }
        }}
      />

      {template ? (
        <TemplateEditor
          template={template}
          selectedVersionId={selectedVersionId}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">Select a template to edit</p>
            <p className="text-xs mt-1 text-muted-foreground">or create a new one with + New</p>
          </div>
        </div>
      )}

      {showCreate && (
        <CreateTemplateModal
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}

      {editingTemplate && (
        <EditTemplateModal
          template={editingTemplate}
          onClose={() => setEditingTemplate(null)}
        />
      )}
    </div>
  )
}
