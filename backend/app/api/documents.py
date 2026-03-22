import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.engines import triggers

from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    project_id: uuid.UUID | None = None,
    type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Document)
    if project_id:
        q = q.filter(Document.project_id == project_id)
    if type:
        q = q.filter(Document.document_type == type)
    if status:
        q = q.filter(Document.status == status)
    return q.all()


@router.post("", response_model=DocumentResponse, status_code=201)
def create_document(body: DocumentCreate, db: Session = Depends(get_db)):
    doc = Document(**body.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(document_id: uuid.UUID, body: DocumentUpdate, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    old_status = doc.status
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    db.commit()
    db.refresh(doc)

    if doc.status != old_status:
        triggers.on_document_status_changed(document_id, db)

    return doc
