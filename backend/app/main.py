from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.middleware.auth import verify_token
from app.api.projects import router as projects_router, areas_router, units_router
from app.api.effort_matrix import router as effort_matrix_router
from app.api.calendars import router as calendars_router
from app.api.objects import router as objects_router
from app.api.documents import router as documents_router
from app.api.workflows import (
    templates_router, entities_router as workflow_entities_router,
    tasks_router as workflow_tasks_router, stages_router as workflow_stages_router,
)
from app.api.dependencies import rules_router, relationships_router, entities_router as dep_entities_router
from app.api.readiness import entities_router as readiness_entities_router, projects_router as readiness_projects_router
from app.api.evidence import router as evidence_router, evidence_router as evidence_delete_router
from app.api.slice import router as slice_router
from app.api.resources import router as resources_router
from app.api.schedule import router as schedule_router
from app.api.export import router as export_router
from app.api.link_templates import router as link_templates_router
from app.api.matrix import router as matrix_router
from app.api.zone_diagrams import areas_router as zone_areas_router, diagrams_router as zone_diagrams_router
from app.api.hierarchy import nodes_router as hierarchy_nodes_router, projects_router as hierarchy_projects_router
from app.api.sprints import releases_router, sprints_router
from app.api.deliverables import router as deliverables_router
from app.api.baselines import projects_router as baselines_projects_router, baselines_router
from app.api.scenarios import projects_router as scenarios_projects_router, scenarios_router
from app.api.integrations import router as integrations_router
from app.api.integration_config import router as integration_config_router
from app.api.bulk import router as bulk_router
from app.api.webhooks import router as webhooks_router

app = FastAPI(
    title="PrismAtlas API",
    description="4D Object-Oriented Project Management Platform — workflow and dependency engine",
    version="0.2.0",
)

# Public paths that bypass auth even when enforce_auth=True
_PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates Supabase JWT Bearer tokens when enforce_auth is enabled."""

    async def dispatch(self, request: Request, call_next):
        if not settings.enforce_auth or request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        token = auth_header[7:]
        try:
            verify_token(token)
        except Exception as exc:
            detail = getattr(exc, "detail", "Token verification failed")
            return JSONResponse({"detail": detail}, status_code=401)

        return await call_next(request)


app.add_middleware(AuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Projects, areas, units
app.include_router(projects_router)
app.include_router(areas_router)
app.include_router(units_router)

# Objects and documents
app.include_router(objects_router)
app.include_router(documents_router)

# Workflow templates and instances
app.include_router(templates_router)
app.include_router(workflow_entities_router)
app.include_router(workflow_tasks_router)
app.include_router(workflow_stages_router)

# Dependency rules and relationships
app.include_router(rules_router)
app.include_router(relationships_router)
app.include_router(dep_entities_router)

# Readiness
app.include_router(readiness_entities_router)
app.include_router(readiness_projects_router)

# Evidence
app.include_router(evidence_router)
app.include_router(evidence_delete_router)

# Slice queries
app.include_router(slice_router)

# Resources (RBS/OBS)
app.include_router(resources_router)

# Schedule / CPM
app.include_router(schedule_router)

# Export (CSV)
app.include_router(export_router)

# Link Templates (FR-4.5.4)
app.include_router(link_templates_router)

# Matrix views (FR-4.6.1, FR-4.6.2)
app.include_router(matrix_router)

# Zone diagrams (FR-4.6.3)
app.include_router(zone_areas_router)
app.include_router(zone_diagrams_router)

# Hierarchy nodes (FR-4.1)
app.include_router(hierarchy_nodes_router)
app.include_router(hierarchy_projects_router)

# Sprints / Agile overlay (FR-4.7)
app.include_router(releases_router)
app.include_router(sprints_router)

# Deliverables (FR-4.3.6)
app.include_router(deliverables_router)

# Baselines + Earned Value (FR-4.4.5)
app.include_router(baselines_projects_router)
app.include_router(baselines_router)

# What-if Scenarios (FR-4.4.6)
app.include_router(scenarios_projects_router)
app.include_router(scenarios_router)

# P6 XER / MS Project export+import, Cradle CSV import (D1)
app.include_router(integrations_router)

# Jira / Azure DevOps integration config + sync (D3)
app.include_router(integration_config_router)

# Bulk object/task operations (D2)
app.include_router(bulk_router)

# Webhooks (D4)
app.include_router(webhooks_router)

# V3 Tier-1: Effort Estimation Matrix (FR-4.3.3)
app.include_router(effort_matrix_router)

# V3 Tier-1: Work Calendars for calendar-aware CPM (FR-4.4.2)
app.include_router(calendars_router)



@app.get("/health")
def health():
    return {"status": "ok"}
