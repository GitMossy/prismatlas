"""
Integration endpoints — P6 XER and MS Project XML export/import,
plus Cradle CSV import.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines.exporters import p6_xer, msproject_xml
from app.engines.importers import p6_xer as p6_importer, cradle_csv

router = APIRouter(prefix="/projects", tags=["integrations"])


@router.get("/{project_id}/export/p6.xer")
def export_p6(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Export project as Primavera P6 XER file."""
    content = p6_xer.export_project_xer(project_id, db)
    if not content:
        raise HTTPException(status_code=404, detail="Project not found")
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=project_{project_id}.xer"},
    )


@router.get("/{project_id}/export/msproject.xml")
def export_msproject(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Export project as Microsoft Project XML file."""
    content = msproject_xml.export_project_xml(project_id, db)
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=project_{project_id}.xml"},
    )


@router.post("/{project_id}/import/p6")
async def import_p6(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Import a Primavera P6 XER file into the project."""
    content = (await file.read()).decode("utf-8", errors="replace")
    result = p6_importer.import_xer(project_id, content, db)
    return result


@router.post("/{project_id}/import/cradle")
async def import_cradle(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Import a Cradle CSV export into the project."""
    content = (await file.read()).decode("utf-8", errors="replace")
    result = cradle_csv.import_cradle_csv(project_id, content, db)
    return result
