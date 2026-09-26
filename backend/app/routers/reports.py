from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.models import AnalysisStatus, PostureAnalysis
from app.routers.analysis import PRIVATE_FILE_HEADERS, get_owned_analysis
from app.services import analysis_service, audit
from app.services.storage import get_storage

router = APIRouter(tags=["reports"])


@router.get("/analyses/{analysis_id}/report")
def download_report(
    request: Request, analysis: PostureAnalysis = Depends(get_owned_analysis), db: Session = Depends(get_db)
) -> FileResponse:
    """The PDF screening report for a completed analysis owned by the current user."""
    if analysis.status != AnalysisStatus.COMPLETED:
        raise NotFoundError("A report is only available for completed analyses.")
    report = analysis_service.ensure_report(db, analysis)
    audit.record(
        db,
        "report.download",
        user_id=analysis.user_id,
        resource_type="report",
        resource_id=analysis.id,
        request=request,
    )
    return FileResponse(
        get_storage().path(report.storage_key),
        media_type="application/pdf",
        filename=f"postureai-report-{analysis.created_at:%Y-%m-%d}.pdf",
        headers=PRIVATE_FILE_HEADERS,
    )
