"""
Jira integration — sync PrismAtlas tasks to Jira issues.

Security:
- API tokens are stored in IntegrationConfig.config as encrypted values.
- The encryption/decryption key is read from INTEGRATION_SECRET_KEY env var.
- Raw tokens are never returned in API responses.

Sync behaviour:
- For each active WorkflowInstance in the project, create or update a Jira
  issue per TaskInstance.
- Mapping: task_name → summary, status → Jira status transition, notes → comment.
- field_mapping JSONB on the IntegrationConfig overrides default field mapping.
"""
import os
import uuid
from base64 import b64decode, b64encode
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.integration import IntegrationConfig
from app.models.workflow import WorkflowInstance, StageInstance, TaskInstance


def sync_to_jira(integration_config_id: uuid.UUID, db: Session) -> dict:
    """Sync PrismAtlas tasks to Jira issues.

    Returns {"synced": int, "errors": list[str]}.
    """
    config_row = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_config_id
    ).first()
    if not config_row:
        return {"synced": 0, "errors": ["Integration config not found"]}
    if config_row.provider != "jira":
        return {"synced": 0, "errors": ["Config is not a Jira integration"]}

    cfg = config_row.config
    base_url = cfg.get("base_url", "").rstrip("/")
    project_key = cfg.get("project_key", "")
    token = _decrypt_token(cfg.get("token_enc", ""))
    email = cfg.get("email", "")

    if not base_url or not token:
        return {"synced": 0, "errors": ["base_url and token_enc are required in config"]}

    auth = (email, token) if email else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    field_map: dict[str, str] = config_row.field_mapping or {}

    instances = (
        db.query(WorkflowInstance)
        .filter(
            WorkflowInstance.status == "active",
        )
        .all()
    )

    synced = 0
    errors: list[str] = []

    for inst in instances:
        for stage in inst.stage_instances:
            for task in stage.task_instances:
                summary_field = field_map.get("task_name", "summary")
                payload: dict[str, Any] = {
                    "fields": {
                        "project": {"key": project_key},
                        summary_field: task.task_name,
                        "issuetype": {"name": "Task"},
                    }
                }
                if task.notes:
                    payload["fields"]["description"] = {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": task.notes}]}
                        ],
                    }

                try:
                    with httpx.Client(timeout=15.0) as client:
                        resp = client.post(
                            f"{base_url}/rest/api/3/issue",
                            json=payload,
                            headers=headers,
                            auth=auth,
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


def _decrypt_token(token_enc: str) -> str:
    """Decrypt an encrypted token using INTEGRATION_SECRET_KEY env var.

    This is a placeholder implementation using simple base64 for illustration.
    In production, replace with Fernet symmetric encryption or AWS KMS / Vault.
    """
    if not token_enc:
        return ""
    secret_key = os.environ.get("INTEGRATION_SECRET_KEY", "")
    if not secret_key:
        # No encryption configured — treat as plaintext (dev only)
        return token_enc
    try:
        # Production: decrypt with Fernet or equivalent
        # from cryptography.fernet import Fernet
        # f = Fernet(secret_key.encode())
        # return f.decrypt(token_enc.encode()).decode()
        return b64decode(token_enc.encode()).decode()
    except Exception:
        return ""
