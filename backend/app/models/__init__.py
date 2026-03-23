# Import all models so Alembic autogenerate can detect them
from app.models.project import Project, Area, Unit
from app.models.object import Object
from app.models.document import Document
from app.models.workflow import (
    WorkflowTemplate,
    WorkflowTemplateVersion,
    WorkflowInstance,
    StageInstance,
    TaskInstance,
)
from app.models.dependency import DependencyRule, Relationship
from app.models.readiness import ReadinessEvaluation
from app.models.evidence import Evidence
from app.models.resource import Resource
from app.models.saved_view import SavedView
from app.models.zone_diagram import ZoneDiagram, ZoneDiagramPin
from app.models.hierarchy import HierarchyNode, EntityHierarchyMembership, HierarchyVersion
from app.models.effort_matrix import EffortMatrixCell
from app.models.calendar import WorkCalendar, CalendarException

__all__ = [
    "Project",
    "Area",
    "Unit",
    "Object",
    "Document",
    "WorkflowTemplate",
    "WorkflowTemplateVersion",
    "WorkflowInstance",
    "StageInstance",
    "TaskInstance",
    "DependencyRule",
    "Relationship",
    "ReadinessEvaluation",
    "Evidence",
    "Resource",
    "SavedView",
    "ZoneDiagram",
    "ZoneDiagramPin",
    "HierarchyNode",
    "EntityHierarchyMembership",
    "HierarchyVersion",
    "EffortMatrixCell",
    "WorkCalendar",
    "CalendarException",
]
