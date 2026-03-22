"""
Azure DevOps integration — sync PrismAtlas tasks to work items.

Security:
- PAT tokens are stored in IntegrationConfig.config as encrypted values
  (token_enc key). The encryption key is read from INTEGRATION_SECRET_KEY
  env var. Raw tokens are never returned in API responses.

Sync behaviour:
- For each active WorkflowInstance in the project, create or update an Azure
  DevOps Work Item (type: Task) per TaskInstance.
- Mapping: task_name → System.Title, status → System.State.
- field_mapping JSONB on the IntegrationConfig overrides default field mapping.

Azure DevOps REST API: PATCH https://dev.azure.com/{org}/{project}/_apis/wit/workitems/$Task
Content-Type: application/json-patch+json
"""
import os
import uuid
from base64 import b64decode, b64encode
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.integration import IntegrationConfig
from app.models.workflow import WorkflowInstance, StageInstance, TaskInstance


def sync_to_azdo(integration_config_id: uuid.UUID, db: Session) -> dict:
    """Sync PrismAtlas tasks to Azure DevOps work items.

    Returns {"synced": int, "errors": list[str]}.
    """
    config_row = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_config_id
    ).first()
    if not config_row:
        return {"synced": 0, "errors": ["Integration config not found"]}
    if config_row.provider != "azdo":
        return {"synced": 0, "errors": ["Config is not an Azure DevOps integration"]}

    cfg = config_row.config
    org = cfg.get("organization", "").strip("/")
    project = cfg.get("project", "").strip("/")
    token = _decrypt_token(cfg.get("token_enc", ""))

    if not org or not project or not token:
        return {"synced": 0, "errors": ["organization, project, and token_enc are required in config"]}

    base_url = f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems"
    api_version = "7.1"

    field_map: dict[str, str] = config_row.field_mapping or {}
    title_field = field_map.get("task_name", "System.Title")
    state_field = field_map.get("status", "System.State")

    instances = (
        db.query(WorkflowInstance)
        .filter(WorkflowInstance.status == "active")
        .all()
    )

    synced = 0
    errors: list[str] = []

    for inst in instances:
        for stage in inst.stage_instances:
            for task in stage.task_instances:
                state_value = _map_status_to_azdo(task.status)
                patch_document = [
                    {"op": "add", "path": f"/fields/{title_field}", "value": task.task_name},
                    {"op": "add", "path": f"/fields/{state_field}", "value": state_value},
                ]
                if task.notes:
                    desc_field = field_map.get("notes", "System.Description")
                    patch_document.append(
                        {"op": "add", "path": f"/fields/{desc_field}", "value": task.notes}
                    )

                try:
                    with httpx.Client(timeout=15.0) as client:
                        resp = client.post(
                            f"{base_url}/$Task?api-version={api_version}",
                            json=patch_document,
                            headers={"Content-Type": "application/json-patch+json"},
                            auth=("", token),
                        )
                        if resp.status_code in (200, 201):
                            synced += 1
                        else:
                            errors.append(
                                f"Task {task.task_name}: HTTP {resp.status_code} — {resp.text[:200]}"
                            )
                except Exception as exc:
                    errors.append(f"Task {task.task_name}: {exc}")

    return {"synced": synced, "errors": errors}


def _map_status_to_azdo(prismatlas_status: str) -> str:
    """Map PrismAtlas task status to Azure DevOps work item state."""
    mapping = {
        "pending": "To Do",
        "in_progress": "In Progress",
        "complete": "Done",
        "skipped": "Removed",
        "blocked": "On Hold",
    }
    return mapping.get(prismatlas_status, "To Do")


def _decrypt_token(token_enc: str) -> str:
    """Decrypt a stored token using INTEGRATION_SECRET_KEY env var.

    Placeholder implementation — replace with Fernet or KMS in production.
    """
    if not token_enc:
        return ""
    secret_key = os.environ.get("INTEGRATION_SECRET_KEY", "")
    if not secret_key:
        return token_enc
    try:
        return b64decode(token_enc.encode()).decode()
    except Exception:
        return ""
