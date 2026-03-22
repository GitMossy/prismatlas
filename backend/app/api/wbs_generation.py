"""
WBS Generation — FR-4.4.1 Automated WBS via Cartesian Product

POST /projects/{project_id}/generate-wbs

Generates WorkflowInstances in bulk by computing the Cartesian product of:
  selected ClassDefinitions × selected HierarchyNodes (e.g. EBS/ZBS nodes)

For each (ClassDefinition, HierarchyNode) pair:
  1. Resolve the active WorkflowTemplateVersion for the ClassDefinition's template.
  2. Create a WorkflowInstance (entity_type='class_set', entity_id=class_definition_id).
  3. Attach an EntityHierarchyMembership linking the class_definition to the node.
  4. Create StageInstances + TaskInstances from the template definition.

Returns a summary of how many instances were created or skipped (already existed).
"""
import uuid
from datetime import datetime, timezone
from itertools import product

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.class_definition import ClassDefinition
from app.models.hierarchy import HierarchyNode, EntityHierarchyMembership
from app.models.workflow import (
    WorkflowInstance,
    WorkflowTemplate,
    WorkflowTemplateVersion,
    StageInstance,
    TaskInstance,
)

router = APIRouter(prefix="/projects", tags=["wbs-generation"])


class WBSGenerateRequest(BaseModel):
    class_definition_ids: list[uuid.UUID]
    hierarchy_node_ids: list[uuid.UUID]
    dry_run: bool = False  # if True, return counts without committing


class WBSGenerateSummary(BaseModel):
    created: int
    skipped: int
    errors: list[str]
    workflow_instance_ids: list[uuid.UUID]


def _instantiate_workflow(
    template_version: WorkflowTemplateVersion,
    entity_type: str,
    entity_id: uuid.UUID,
    db: Session,
) -> WorkflowInstance:
    """Clone a template version into a live WorkflowInstance with Stage/Task rows."""
    now = datetime.now(timezone.utc)
    instance = WorkflowInstance(
        entity_type=entity_type,
        entity_id=entity_id,
        template_version_id=template_version.id,
        status="active",
    )
    db.add(instance)
    db.flush()  # get instance.id

    definition = template_version.definition or {}
    for stage_def in definition.get("stages", []):
        stage_inst = StageInstance(
            workflow_instance_id=instance.id,
            stage_key=stage_def["key"],
            stage_name=stage_def["name"],
            stage_order=stage_def.get("order", 1),
            status="pending",
        )
        db.add(stage_inst)
        db.flush()

        for task_def in stage_def.get("tasks", []):
            task_inst = TaskInstance(
                stage_instance_id=stage_inst.id,
                task_key=task_def["key"],
                task_name=task_def["name"],
                task_order=task_def.get("order", 1),
                is_mandatory=task_def.get("is_mandatory", True),
                status="pending",
                duration_days=float(task_def.get("duration_days", 1.0)),
                effort_hours=task_def.get("effort_hours"),
            )
            db.add(task_inst)

    return instance


@router.post("/{project_id}/generate-wbs", response_model=WBSGenerateSummary)
def generate_wbs(
    project_id: uuid.UUID,
    body: WBSGenerateRequest,
    db: Session = Depends(get_db),
):
    """
    Generate WorkflowInstances for each (ClassDefinition × HierarchyNode) pair.

    Skips pairs where a WorkflowInstance already exists for that class_definition_id
    to support idempotent re-runs.
    """
    created_ids: list[uuid.UUID] = []
    skipped = 0
    errors: list[str] = []

    # Validate inputs
    class_defs = (
        db.query(ClassDefinition)
        .filter(
            ClassDefinition.id.in_(body.class_definition_ids),
            ClassDefinition.project_id == project_id,
        )
        .all()
    )
    found_cd_ids = {cd.id for cd in class_defs}
    for missing in set(body.class_definition_ids) - found_cd_ids:
        errors.append(f"ClassDefinition {missing} not found in project {project_id}")

    nodes = (
        db.query(HierarchyNode)
        .filter(
            HierarchyNode.id.in_(body.hierarchy_node_ids),
            HierarchyNode.project_id == project_id,
        )
        .all()
    )
    found_node_ids = {n.id for n in nodes}
    for missing in set(body.hierarchy_node_ids) - found_node_ids:
        errors.append(f"HierarchyNode {missing} not found in project {project_id}")

    if errors and not (class_defs and nodes):
        raise HTTPException(status_code=422, detail=errors)

    for cd, node in product(class_defs, nodes):
        # Skip if a workflow instance already exists for this class_definition
        existing = (
            db.query(WorkflowInstance)
            .filter(
                WorkflowInstance.entity_type == "class_set",
                WorkflowInstance.entity_id == cd.id,
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        # Resolve active template version
        if not cd.workflow_template_id:
            errors.append(
                f"ClassDefinition '{cd.name}' ({cd.id}) has no workflow template assigned — skipped"
            )
            skipped += 1
            continue

        template_version = (
            db.query(WorkflowTemplateVersion)
            .filter(
                WorkflowTemplateVersion.template_id == cd.workflow_template_id,
                WorkflowTemplateVersion.is_active == True,  # noqa: E712
            )
            .order_by(WorkflowTemplateVersion.version_number.desc())
            .first()
        )
        if not template_version:
            errors.append(
                f"No active template version for template {cd.workflow_template_id} — skipped"
            )
            skipped += 1
            continue

        if body.dry_run:
            created_ids.append(cd.id)  # placeholder; no DB write
            continue

        instance = _instantiate_workflow(
            template_version=template_version,
            entity_type="class_set",
            entity_id=cd.id,
            db=db,
        )

        # Link the class_definition to the hierarchy node
        existing_membership = (
            db.query(EntityHierarchyMembership)
            .filter(
                EntityHierarchyMembership.entity_id == cd.id,
                EntityHierarchyMembership.node_id == node.id,
            )
            .first()
        )
        if not existing_membership:
            db.add(EntityHierarchyMembership(
                entity_type="class_set",
                entity_id=cd.id,
                node_id=node.id,
            ))

        created_ids.append(instance.id)

    if not body.dry_run:
        db.commit()

    return WBSGenerateSummary(
        created=len(created_ids),
        skipped=skipped,
        errors=errors,
        workflow_instance_ids=created_ids,
    )
