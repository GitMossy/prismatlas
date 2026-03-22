"""
Integration configuration API — manage Jira and Azure DevOps integrations
per project, and trigger syncs.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.integration import IntegrationConfig, VALID_PROVIDERS
from app.engines.integrations import jira, azure_devops

router = APIRouter(prefix="/projects", tags=["integrations"])


@router.post("/{project_id}/integrations")
def create_integration(
    project_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
):
    """Create an integration config for this project.

    Required body fields: provider ('jira' | 'azdo'), config (dict).
    Optional: field_mapping (dict), sync_direction ('push' | 'pull' | 'bidirectional').
    """
    provider = body.get("provider", "")
    if provider not in VALID_PROVIDERS:
        raise HTTPException(400, f"provider must be one of {VALID_PROVIDERS}")

    config_data = body.get("config")
    if not config_data or not isinstance(config_data, dict):
        raise HTTPException(400, "config dict is required")

    cfg = IntegrationConfig(
        project_id=project_id,
        provider=provider,
        config=config_data,
        field_mapping=body.get("field_mapping", {}),
        sync_direction=body.get("sync_direction", "push"),
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)

    # Never return raw config (may contain sensitive fields) — return safe subset
    return _safe_response(cfg)


@router.get("/{project_id}/integrations")
def list_integrations(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """List all integration configs for this project (config field redacted)."""
    rows = db.query(IntegrationConfig).filter(IntegrationConfig.project_id == project_id).all()
    return [_safe_response(r) for r in rows]


@router.get("/{project_id}/integrations/{integration_id}")
def get_integration(
    project_id: uuid.UUID,
    integration_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get a single integration config (config field redacted)."""
    row = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_id,
        IntegrationConfig.project_id == project_id,
    ).first()
    if not row:
        raise HTTPException(404, "Integration config not found")
    return _safe_response(row)


@router.delete("/{project_id}/integrations/{integration_id}", status_code=204)
def delete_integration(
    project_id: uuid.UUID,
    integration_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Delete an integration config."""
    row = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_id,
        IntegrationConfig.project_id == project_id,
    ).first()
    if not row:
        raise HTTPException(404, "Integration config not found")
    db.delete(row)
    db.commit()


@router.post("/{project_id}/integrations/{provider}/sync")
def sync_integration(
    project_id: uuid.UUID,
    provider: str,
    db: Session = Depends(get_db),
):
    """Trigger a sync for the given provider ('jira' or 'azdo').

    Finds the first active integration config for this project+provider and
    runs the sync. Returns {"synced": int, "errors": list}.
    """
    if provider not in VALID_PROVIDERS:
        raise HTTPException(400, f"provider must be one of {VALID_PROVIDERS}")

    config_row = db.query(IntegrationConfig).filter(
        IntegrationConfig.project_id == project_id,
        IntegrationConfig.provider == provider,
    ).first()

    if not config_row:
        raise HTTPException(404, f"No {provider} integration configured for this project")

    if provider == "jira":
        result = jira.sync_to_jira(config_row.id, db)
    else:
        result = azure_devops.sync_to_azdo(config_row.id, db)

    # Update last_synced_at
    from datetime import datetime, timezone
    config_row.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    return result


def _safe_response(cfg: IntegrationConfig) -> dict:
    """Return integration config without exposing raw secrets."""
    config_safe = {k: v for k, v in (cfg.config or {}).items() if "token" not in k.lower()}
    return {
        "id": str(cfg.id),
        "project_id": str(cfg.project_id),
        "provider": cfg.provider,
        "config": config_safe,
        "field_mapping": cfg.field_mapping,
        "sync_direction": cfg.sync_direction,
        "last_synced_at": cfg.last_synced_at.isoformat() if cfg.last_synced_at else None,
        "created_at": cfg.created_at.isoformat() if cfg.created_at else None,
    }
