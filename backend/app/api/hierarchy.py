"""
Hierarchy API — FR-4.1

Unlimited-depth hierarchy nodes across five dimensions (ZBS/OBS/TBS/VBS/RBS).

Endpoints:
  GET    /hierarchy-nodes?project_id=&dimension=   — list nodes (tree)
  POST   /hierarchy-nodes                          — create node
  GET    /hierarchy-nodes/{id}                     — get node
  PUT    /hierarchy-nodes/{id}                     — update node
  DELETE /hierarchy-nodes/{id}                     — delete node
  PATCH  /hierarchy-nodes/{id}/move                — move (parent + position)
  POST   /projects/{id}/hierarchy/import           — bulk CSV import
  GET    /projects/{id}/hierarchy/diff?v1=&v2=     — diff two versions
"""
import csv
import io
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from datetime import datetime, timezone

from app.database import get_db
from app.models.project import Project
from app.models.hierarchy import HierarchyNode, HierarchyVersion, EntityHierarchyMembership, HIERARCHY_DIMENSIONS
from app.models.object import Object as ProjectObject
from app.models.workflow import WorkflowTemplate, WorkflowTemplateVersion, WorkflowInstance, StageInstance, TaskInstance
from app.models.dependency import DependencyRule

nodes_router = APIRouter(prefix="/hierarchy-nodes", tags=["hierarchy"])
projects_router = APIRouter(prefix="/projects", tags=["hierarchy"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class HierarchyNodeCreate(BaseModel):
    project_id: uuid.UUID
    dimension: str
    name: str
    description: str | None = None
    parent_id: uuid.UUID | None = None
    position: int = 0
    workflow_template_id: uuid.UUID | None = None
    depends_on_node_id: uuid.UUID | None = None
    dependency_condition: dict | None = None


class HierarchyNodeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    position: int | None = None
    workflow_template_id: uuid.UUID | None = None
    depends_on_node_id: uuid.UUID | None = None
    dependency_condition: dict | None = None


class HierarchyNodeMove(BaseModel):
    parent_id: uuid.UUID | None = None
    position: int = 0


class HierarchyNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    dimension: str
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    position: int
    workflow_template_id: uuid.UUID | None = None
    workflow_template_name: str | None = None
    depends_on_node_id: uuid.UUID | None = None
    depends_on_node_name: str | None = None
    dependency_condition: dict | None = None
    children: list["HierarchyNodeOut"] = []


HierarchyNodeOut.model_rebuild()


class HierarchyVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    dimension: str
    snapshot: dict[str, Any]
    label: str


class ImportResult(BaseModel):
    created: int
    errors: list[str]


class DiffResult(BaseModel):
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    modified: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Helper: build tree from flat list
# ---------------------------------------------------------------------------

def _build_tree(nodes: list[HierarchyNode], node_name_map: dict[uuid.UUID, str] | None = None) -> list[dict[str, Any]]:
    """Convert flat list of nodes into nested tree structure."""
    # Build a name lookup for depends_on_node_name resolution
    if node_name_map is None:
        node_name_map = {n.id: n.name for n in nodes}
    node_map: dict[uuid.UUID, dict] = {}
    for n in nodes:
        node_map[n.id] = {
            "id": str(n.id),
            "project_id": str(n.project_id),
            "dimension": n.dimension,
            "name": n.name,
            "description": n.description,
            "parent_id": str(n.parent_id) if n.parent_id else None,
            "position": n.position,
            "workflow_template_id": str(n.workflow_template_id) if n.workflow_template_id else None,
            "workflow_template_name": n.workflow_template.name if n.workflow_template else None,
            "depends_on_node_id": str(n.depends_on_node_id) if n.depends_on_node_id else None,
            "depends_on_node_name": node_name_map.get(n.depends_on_node_id) if n.depends_on_node_id else None,
            "dependency_condition": n.dependency_condition,
            "children": [],
        }
    roots: list[dict] = []
    for n in nodes:
        entry = node_map[n.id]
        if n.parent_id and n.parent_id in node_map:
            node_map[n.parent_id]["children"].append(entry)
        else:
            roots.append(entry)
    # Sort children by position
    def _sort(nodes_list: list) -> None:
        nodes_list.sort(key=lambda x: x["position"])
        for node in nodes_list:
            _sort(node["children"])
    _sort(roots)
    return roots


def _snapshot_tree(nodes: list[HierarchyNode]) -> dict[str, Any]:
    """Produce a JSON snapshot of the current hierarchy for versioning."""
    return {"nodes": _build_tree(nodes)}


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@nodes_router.get("", response_model=list[dict])
def list_hierarchy_nodes(
    project_id: uuid.UUID = Query(...),
    dimension: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(HierarchyNode).filter(HierarchyNode.project_id == project_id)
    if dimension:
        if dimension not in HIERARCHY_DIMENSIONS:
            raise HTTPException(status_code=422, detail=f"dimension must be one of {HIERARCHY_DIMENSIONS}")
        q = q.filter(HierarchyNode.dimension == dimension)
    nodes = q.order_by(HierarchyNode.position).all()
    return _build_tree(nodes)


@nodes_router.post("", status_code=201)
def create_hierarchy_node(body: HierarchyNodeCreate, db: Session = Depends(get_db)):
    if body.dimension not in HIERARCHY_DIMENSIONS:
        raise HTTPException(status_code=422, detail=f"dimension must be one of {HIERARCHY_DIMENSIONS}")
    project = db.query(Project).filter(Project.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.parent_id:
        parent = db.query(HierarchyNode).filter(HierarchyNode.id == body.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent node not found")
        if parent.dimension != body.dimension:
            raise HTTPException(status_code=422, detail="Parent node is in a different dimension")
    node = HierarchyNode(**body.model_dump())
    db.add(node)
    db.commit()
    db.refresh(node)
    return {"id": str(node.id), "project_id": str(node.project_id), "dimension": node.dimension,
            "name": node.name, "description": node.description,
            "parent_id": str(node.parent_id) if node.parent_id else None,
            "position": node.position,
            "workflow_template_id": str(node.workflow_template_id) if node.workflow_template_id else None,
            "workflow_template_name": None,
            "children": []}


@nodes_router.get("/{node_id}")
def get_hierarchy_node(node_id: uuid.UUID, db: Session = Depends(get_db)):
    node = db.query(HierarchyNode).filter(HierarchyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    # Build subtree from this node
    all_nodes = (
        db.query(HierarchyNode)
        .filter(
            HierarchyNode.project_id == node.project_id,
            HierarchyNode.dimension == node.dimension,
        )
        .all()
    )
    tree = _build_tree(all_nodes)

    def _find(nodes_list: list, target_id: str) -> dict | None:
        for n in nodes_list:
            if n["id"] == target_id:
                return n
            found = _find(n["children"], target_id)
            if found:
                return found
        return None

    return _find(tree, str(node_id)) or {}


@nodes_router.put("/{node_id}")
def update_hierarchy_node(
    node_id: uuid.UUID,
    body: HierarchyNodeUpdate,
    db: Session = Depends(get_db),
):
    node = db.query(HierarchyNode).filter(HierarchyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if body.name is not None:
        node.name = body.name
    if body.description is not None:
        node.description = body.description
    if body.position is not None:
        node.position = body.position
    if "workflow_template_id" in body.model_fields_set:
        node.workflow_template_id = body.workflow_template_id
    if "depends_on_node_id" in body.model_fields_set:
        node.depends_on_node_id = body.depends_on_node_id
    if "dependency_condition" in body.model_fields_set:
        node.dependency_condition = body.dependency_condition
    db.commit()
    db.refresh(node)
    template_name = None
    if node.workflow_template_id:
        tmpl = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == node.workflow_template_id).first()
        template_name = tmpl.name if tmpl else None
    dep_node_name = None
    if node.depends_on_node_id:
        dep_node = db.query(HierarchyNode).filter(HierarchyNode.id == node.depends_on_node_id).first()
        dep_node_name = dep_node.name if dep_node else None
    return {"id": str(node.id), "name": node.name, "description": node.description,
            "position": node.position,
            "workflow_template_id": str(node.workflow_template_id) if node.workflow_template_id else None,
            "workflow_template_name": template_name,
            "depends_on_node_id": str(node.depends_on_node_id) if node.depends_on_node_id else None,
            "depends_on_node_name": dep_node_name,
            "dependency_condition": node.dependency_condition}


@nodes_router.delete("/{node_id}", status_code=204)
def delete_hierarchy_node(node_id: uuid.UUID, db: Session = Depends(get_db)):
    node = db.query(HierarchyNode).filter(HierarchyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(node)
    db.commit()


class MembershipCreate(BaseModel):
    entity_type: str  # 'object' | 'document'
    entity_id: uuid.UUID


class MemberOut(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    name: str
    object_type: str | None = None  # populated for entity_type='object'


@nodes_router.get("/{node_id}/members", response_model=list[MemberOut])
def list_node_members(node_id: uuid.UUID, db: Session = Depends(get_db)):
    node = db.query(HierarchyNode).filter(HierarchyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    memberships = (
        db.query(EntityHierarchyMembership)
        .filter(EntityHierarchyMembership.node_id == node_id)
        .all()
    )
    results = []
    for m in memberships:
        if m.entity_type == "object":
            obj = db.query(ProjectObject).filter(ProjectObject.id == m.entity_id).first()
            if obj:
                results.append(MemberOut(entity_type="object", entity_id=m.entity_id,
                                         name=obj.name, object_type=obj.object_type))
        else:
            results.append(MemberOut(entity_type=m.entity_type, entity_id=m.entity_id, name=str(m.entity_id)))
    return results


@nodes_router.post("/{node_id}/members", status_code=201, response_model=MemberOut)
def add_node_member(node_id: uuid.UUID, body: MembershipCreate, db: Session = Depends(get_db)):
    node = db.query(HierarchyNode).filter(HierarchyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    existing = db.query(EntityHierarchyMembership).filter(
        EntityHierarchyMembership.node_id == node_id,
        EntityHierarchyMembership.entity_id == body.entity_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Entity already a member of this node")
    membership = EntityHierarchyMembership(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        node_id=node_id,
    )
    db.add(membership)
    db.flush()

    # Auto-assign workflow: walk up the node tree to find the nearest workflow_template_id
    workflow_template_id = _resolve_workflow_template(node, db)
    if workflow_template_id and body.entity_type == "object":
        _auto_instantiate_workflow(body.entity_id, workflow_template_id, body.entity_type, db)

    # Auto-create cross-object dependency rules if this node depends on another node
    if body.entity_type == "object" and node.depends_on_node_id and node.dependency_condition:
        _create_dependency_rules_for_member(
            source_id=body.entity_id,
            source_node_id=node.id,
            depends_on_node_id=node.depends_on_node_id,
            condition=node.dependency_condition,
            project_id=node.project_id,
            db=db,
        )

    db.commit()
    name = str(body.entity_id)
    object_type = None
    if body.entity_type == "object":
        obj = db.query(ProjectObject).filter(ProjectObject.id == body.entity_id).first()
        if obj:
            name = obj.name
            object_type = obj.object_type
    return MemberOut(entity_type=body.entity_type, entity_id=body.entity_id,
                     name=name, object_type=object_type)


def _resolve_workflow_template(node: HierarchyNode, db: Session) -> uuid.UUID | None:
    """Walk up the hierarchy to find the nearest assigned workflow_template_id."""
    current: HierarchyNode | None = node
    while current is not None:
        if current.workflow_template_id:
            return current.workflow_template_id
        if current.parent_id:
            current = db.query(HierarchyNode).filter(HierarchyNode.id == current.parent_id).first()
        else:
            break
    return None


def _auto_instantiate_workflow(
    entity_id: uuid.UUID,
    template_id: uuid.UUID,
    entity_type: str,
    db: Session,
) -> None:
    """Instantiate the latest active version of a template on an entity if not already active."""
    # Skip if entity already has an active workflow
    existing = db.query(WorkflowInstance).filter(
        WorkflowInstance.entity_id == entity_id,
        WorkflowInstance.status == "active",
    ).first()
    if existing:
        return

    # Find latest active version of the template
    version = (
        db.query(WorkflowTemplateVersion)
        .filter(
            WorkflowTemplateVersion.template_id == template_id,
            WorkflowTemplateVersion.is_active == True,
        )
        .order_by(WorkflowTemplateVersion.version_number.desc())
        .first()
    )
    if not version:
        # Fall back to any latest version
        version = (
            db.query(WorkflowTemplateVersion)
            .filter(WorkflowTemplateVersion.template_id == template_id)
            .order_by(WorkflowTemplateVersion.version_number.desc())
            .first()
        )
    if not version:
        return

    instance = WorkflowInstance(
        entity_type=entity_type,
        entity_id=entity_id,
        template_version_id=version.id,
        status="active",
    )
    db.add(instance)
    db.flush()

    stages = sorted(version.definition.get("stages", []), key=lambda s: s["order"])
    for i, stage_def in enumerate(stages):
        stage = StageInstance(
            workflow_instance_id=instance.id,
            stage_key=stage_def["key"],
            stage_name=stage_def["name"],
            stage_order=stage_def["order"],
            status="active" if i == 0 else "pending",
            started_at=datetime.now(timezone.utc) if i == 0 else None,
        )
        db.add(stage)
        db.flush()

        for task_def in sorted(stage_def.get("tasks", []), key=lambda t: t["order"]):
            task = TaskInstance(
                stage_instance_id=stage.id,
                task_key=task_def["key"],
                task_name=task_def["name"],
                task_order=task_def["order"],
                is_mandatory=task_def.get("is_mandatory", True),
                duration_days=task_def.get("duration_days", 1.0),
                effort_hours=task_def.get("effort_hours"),
            )
            db.add(task)


_AUTO_DEP_PREFIX = "auto-node-dep:"


def _create_dependency_rules_for_member(
    source_id: uuid.UUID,
    source_node_id: uuid.UUID,
    depends_on_node_id: uuid.UUID,
    condition: dict,
    project_id: uuid.UUID,
    db: Session,
) -> None:
    """Create DependencyRule records from source_id to every object in depends_on_node."""
    target_memberships = (
        db.query(EntityHierarchyMembership)
        .filter(
            EntityHierarchyMembership.node_id == depends_on_node_id,
            EntityHierarchyMembership.entity_type == "object",
        )
        .all()
    )
    auto_tag = f"{_AUTO_DEP_PREFIX}{source_node_id}"
    for tm in target_memberships:
        # Skip if rule already exists
        existing = db.query(DependencyRule).filter(
            DependencyRule.source_entity_id == source_id,
            DependencyRule.target_entity_id == tm.entity_id,
            DependencyRule.description == auto_tag,
        ).first()
        if existing:
            continue
        rule = DependencyRule(
            name=f"Node dependency: {source_node_id} → {depends_on_node_id}",
            description=auto_tag,
            source_entity_type="object",
            source_entity_id=source_id,
            target_entity_type="object",
            target_entity_id=tm.entity_id,
            condition=condition,
            is_mandatory=True,
            project_id=project_id,
            link_type="FS",
            lag_days=0.0,
        )
        db.add(rule)
    db.flush()


def _remove_auto_dependency_rules(entity_id: uuid.UUID, node_id: uuid.UUID, db: Session) -> None:
    """Remove DependencyRules auto-created when this entity was assigned to this node."""
    auto_tag = f"{_AUTO_DEP_PREFIX}{node_id}"
    db.query(DependencyRule).filter(
        DependencyRule.source_entity_id == entity_id,
        DependencyRule.description == auto_tag,
    ).delete(synchronize_session=False)


@nodes_router.delete("/{node_id}/members/{entity_id}", status_code=204)
def remove_node_member(node_id: uuid.UUID, entity_id: uuid.UUID, db: Session = Depends(get_db)):
    membership = db.query(EntityHierarchyMembership).filter(
        EntityHierarchyMembership.node_id == node_id,
        EntityHierarchyMembership.entity_id == entity_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    # Remove auto-created dependency rules originating from this node assignment
    _remove_auto_dependency_rules(entity_id, node_id, db)
    db.delete(membership)
    db.commit()


@nodes_router.patch("/{node_id}/move")
def move_hierarchy_node(
    node_id: uuid.UUID,
    body: HierarchyNodeMove,
    db: Session = Depends(get_db),
):
    node = db.query(HierarchyNode).filter(HierarchyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if body.parent_id:
        parent = db.query(HierarchyNode).filter(HierarchyNode.id == body.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent node not found")
        if parent.dimension != node.dimension:
            raise HTTPException(status_code=422, detail="Cannot move node to different dimension")
        # Prevent circular reference
        if str(body.parent_id) == str(node_id):
            raise HTTPException(status_code=422, detail="Node cannot be its own parent")
    node.parent_id = body.parent_id
    node.position = body.position
    db.commit()
    db.refresh(node)
    return {"id": str(node.id), "parent_id": str(node.parent_id) if node.parent_id else None,
            "position": node.position}


# ---------------------------------------------------------------------------
# Project-scoped: bulk import + diff
# ---------------------------------------------------------------------------

@projects_router.post("/{project_id}/hierarchy/import", response_model=ImportResult)
def import_hierarchy_csv(
    project_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
):
    """
    Bulk CSV import. Body: {"csv_content": "<csv string>"}
    CSV columns: dimension, path (slash-separated), name
    Example row: ZBS,Area1/Zone1/SubZone,SubZone
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    csv_content: str = body.get("csv_content", "")
    if not csv_content:
        raise HTTPException(status_code=422, detail="csv_content is required")

    reader = csv.DictReader(io.StringIO(csv_content))
    created = 0
    errors: list[str] = []

    # Cache of (dimension, path) → node id to avoid re-querying
    path_cache: dict[tuple[str, str], uuid.UUID] = {}

    for row_num, row in enumerate(reader, start=2):
        try:
            dimension = (row.get("dimension") or "").strip().upper()
            path = (row.get("path") or "").strip()
            name = (row.get("name") or "").strip()

            if dimension not in HIERARCHY_DIMENSIONS:
                errors.append(f"Row {row_num}: invalid dimension '{dimension}'")
                continue
            if not path or not name:
                errors.append(f"Row {row_num}: path and name are required")
                continue

            parts = [p.strip() for p in path.split("/") if p.strip()]
            parent_id: uuid.UUID | None = None

            # Walk/create path segments
            for depth, part in enumerate(parts):
                current_path = "/".join(parts[: depth + 1])
                cache_key = (dimension, current_path)
                if cache_key in path_cache:
                    parent_id = path_cache[cache_key]
                    continue
                # Look up existing node
                existing = (
                    db.query(HierarchyNode)
                    .filter(
                        HierarchyNode.project_id == project_id,
                        HierarchyNode.dimension == dimension,
                        HierarchyNode.name == part,
                        HierarchyNode.parent_id == parent_id,
                    )
                    .first()
                )
                if existing:
                    path_cache[cache_key] = existing.id
                    parent_id = existing.id
                else:
                    node = HierarchyNode(
                        project_id=project_id,
                        dimension=dimension,
                        name=part,
                        parent_id=parent_id,
                    )
                    db.add(node)
                    db.flush()
                    path_cache[cache_key] = node.id
                    parent_id = node.id
                    created += 1

        except Exception as exc:
            errors.append(f"Row {row_num}: {exc}")

    db.commit()
    return ImportResult(created=created, errors=errors)


class NodeMembershipOut(BaseModel):
    node_id: uuid.UUID
    entity_id: uuid.UUID
    entity_type: str
    name: str
    object_type: str | None = None
    status: str | None = None


@projects_router.get("/{project_id}/hierarchy/memberships", response_model=list[NodeMembershipOut])
def list_project_hierarchy_memberships(
    project_id: uuid.UUID,
    dimension: str = Query(default="ZBS"),
    db: Session = Depends(get_db),
):
    """Return all entity memberships for every node in a given dimension — single query for dashboard rollup."""
    if dimension not in HIERARCHY_DIMENSIONS:
        raise HTTPException(status_code=422, detail=f"dimension must be one of {HIERARCHY_DIMENSIONS}")
    node_ids = [
        n.id for n in db.query(HierarchyNode.id)
        .filter(HierarchyNode.project_id == project_id, HierarchyNode.dimension == dimension)
        .all()
    ]
    if not node_ids:
        return []
    memberships = (
        db.query(EntityHierarchyMembership)
        .filter(EntityHierarchyMembership.node_id.in_(node_ids))
        .all()
    )
    results = []
    for m in memberships:
        name = str(m.entity_id)
        object_type = None
        status = None
        if m.entity_type == "object":
            obj = db.query(ProjectObject).filter(ProjectObject.id == m.entity_id).first()
            if obj:
                name = obj.name
                object_type = obj.object_type
                status = obj.status
        results.append(NodeMembershipOut(
            node_id=m.node_id,
            entity_id=m.entity_id,
            entity_type=m.entity_type,
            name=name,
            object_type=object_type,
            status=status,
        ))
    return results


@projects_router.get("/{project_id}/hierarchy/diff", response_model=DiffResult)
def diff_hierarchy_versions(
    project_id: uuid.UUID,
    v1: uuid.UUID = Query(...),
    v2: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
):
    """Compare two hierarchy version snapshots."""
    ver1 = db.query(HierarchyVersion).filter(
        HierarchyVersion.id == v1, HierarchyVersion.project_id == project_id
    ).first()
    ver2 = db.query(HierarchyVersion).filter(
        HierarchyVersion.id == v2, HierarchyVersion.project_id == project_id
    ).first()
    if not ver1 or not ver2:
        raise HTTPException(status_code=404, detail="One or both versions not found")

    def _flatten(nodes_list: list, parent_path: str = "") -> dict[str, dict]:
        result = {}
        for n in nodes_list:
            path = f"{parent_path}/{n['name']}" if parent_path else n["name"]
            result[path] = {"name": n["name"], "id": n["id"], "position": n["position"]}
            result.update(_flatten(n.get("children", []), path))
        return result

    nodes1 = _flatten(ver1.snapshot.get("nodes", []))
    nodes2 = _flatten(ver2.snapshot.get("nodes", []))

    added = [{"path": k, **v} for k, v in nodes2.items() if k not in nodes1]
    removed = [{"path": k, **v} for k, v in nodes1.items() if k not in nodes2]
    modified = [
        {"path": k, "v1": nodes1[k], "v2": nodes2[k]}
        for k in nodes1
        if k in nodes2 and nodes1[k] != nodes2[k]
    ]

    return DiffResult(added=added, removed=removed, modified=modified)
