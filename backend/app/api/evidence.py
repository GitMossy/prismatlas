import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evidence import Evidence
from app.models.workflow import TaskInstance
from app.schemas.evidence import EvidenceResponse
from app.storage import upload_evidence, delete_evidence

router = APIRouter(prefix="/tasks", tags=["evidence"])
evidence_router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("/{task_id}/evidence", response_model=EvidenceResponse, status_code=201)
async def upload_task_evidence(
    task_id: uuid.UUID,
    uploaded_by: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    task = db.query(TaskInstance).filter(TaskInstance.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    data = await file.read()
    file_url = upload_evidence(
        task_instance_id=str(task_id),
        filename=file.filename,
        data=data,
        content_type=file.content_type or "application/octet-stream",
    )

    evidence = Evidence(
        task_instance_id=task_id,
        file_name=file.filename,
        file_url=file_url,
        description=description,
        uploaded_by=uploaded_by,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/{task_id}/evidence", response_model=list[EvidenceResponse])
def list_task_evidence(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = db.query(TaskInstance).filter(TaskInstance.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db.query(Evidence).filter(Evidence.task_instance_id == task_id).all()


@evidence_router.delete("/{evidence_id}", status_code=204)
def delete_evidence_record(evidence_id: uuid.UUID, db: Session = Depends(get_db)):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    delete_evidence(task_instance_id=str(evidence.task_instance_id), filename=evidence.file_name)
    db.delete(evidence)
    db.commit()
