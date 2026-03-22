from functools import lru_cache

from supabase import create_client, Client

from app.config import settings

EVIDENCE_BUCKET = "evidence"


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


def upload_evidence(task_instance_id: str, filename: str, data: bytes, content_type: str) -> str:
    """
    Upload an evidence file to Supabase Storage.
    Returns the public URL of the uploaded file.
    Path: evidence/{task_instance_id}/{filename}
    """
    client = get_supabase()
    path = f"{task_instance_id}/{filename}"
    client.storage.from_(EVIDENCE_BUCKET).upload(
        path=path,
        file=data,
        file_options={"content-type": content_type},
    )
    return client.storage.from_(EVIDENCE_BUCKET).get_public_url(path)


def delete_evidence(task_instance_id: str, filename: str) -> None:
    client = get_supabase()
    path = f"{task_instance_id}/{filename}"
    client.storage.from_(EVIDENCE_BUCKET).remove([path])
