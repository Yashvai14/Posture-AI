import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, PayloadTooLargeError
from app.core.rate_limit import upload_limiter
from app.db.session import get_db
from app.models.models import PostureAnalysis, User
from app.repositories import repository as repo
from app.routers.deps import get_current_user
from app.schemas.schemas import AnalysisCreate, AnalysisOut, AnalysisPage, AnalysisSummaryOut, ProgressOut
from app.services import analysis_service, audit
from app.services.image_validation import read_limited, validate_image
from app.services.storage import get_storage

router = APIRouter(tags=["analyses"])

PRIVATE_FILE_HEADERS = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}


class AnalysisCreated(BaseModel):
    id: uuid.UUID
    status: str


def get_owned_analysis(
    analysis_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PostureAnalysis:
    analysis = repo.get_analysis_for_user(db, analysis_id, user.id)
    if analysis is None:
        # 404 rather than 403, so the existence of other users' analyses is not revealed.
        raise NotFoundError("Analysis not found.")
    return analysis


def reject_oversized_request(request: Request) -> None:
    length = request.headers.get("content-length")
    limit = get_settings().max_upload_bytes + 64 * 1024  # allowance for the other form fields
    if length and length.isdigit() and int(length) > limit:
        raise PayloadTooLargeError(f"The upload is larger than {get_settings().MAX_UPLOAD_MB} MB.")


@router.post(
    "/analyses",
    response_model=AnalysisCreated,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(reject_oversized_request)],
)
async def create_analysis(
    request: Request,
    image: UploadFile = File(...),
    date_of_birth: Annotated[str | None, Form()] = None,
    sex: Annotated[str | None, Form()] = None,
    height_cm: Annotated[str | None, Form()] = None,
    weight_kg: Annotated[str | None, Form()] = None,
    symptoms: Annotated[str | None, Form()] = None,
    save_to_profile: Annotated[bool, Form()] = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisCreated:
    """Accepts a photo and profile snapshot; analysis runs in the background. Poll GET /analyses/{id}."""
    fields = {
        "date_of_birth": date_of_birth,
        "sex": sex,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "symptoms": symptoms,
    }
    try:
        data = AnalysisCreate(
            **{k: v for k, v in fields.items() if v not in (None, "")}, save_to_profile=save_to_profile
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_url=False)) from None
    settings = get_settings()
    upload_limiter.check(str(user.id))
    raw = await read_limited(image, settings.max_upload_bytes)
    validated = validate_image(raw, image.filename, image.content_type, settings.MAX_IMAGE_PIXELS)
    analysis = analysis_service.create_analysis(db, user, validated, data, request)
    db.refresh(analysis)
    return AnalysisCreated(id=analysis.id, status=analysis.status.value)


@router.get("/analyses", response_model=AnalysisPage)
def list_analyses(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisPage:
    items, total = repo.list_analyses_for_user(db, user.id, limit, offset)
    return AnalysisPage(
        items=[
            AnalysisSummaryOut(
                id=a.id,
                status=a.status.value,
                view=a.view.value if a.view else None,
                created_at=a.created_at,
                alignment_score=a.alignment_score,
                findings=a.findings,
                symptoms=a.snapshot.symptoms if a.snapshot else None,
            )
            for a in items
        ],
        total=total,
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def read_analysis(analysis: PostureAnalysis = Depends(get_owned_analysis)) -> AnalysisOut:
    return analysis_service.to_out(analysis)


def _file_response(key: str | None, media_type: str, filename: str) -> FileResponse:
    storage = get_storage()
    if not storage.exists(key):
        raise NotFoundError("File not found.")
    return FileResponse(
        storage.path(key),
        media_type=media_type,
        filename=filename,
        headers=PRIVATE_FILE_HEADERS,
        content_disposition_type="inline",
    )


@router.get("/analyses/{analysis_id}/image")
def original_image(
    request: Request, analysis: PostureAnalysis = Depends(get_owned_analysis), db: Session = Depends(get_db)
) -> FileResponse:
    audit.record(
        db,
        "file.view",
        user_id=analysis.user_id,
        resource_type="analysis_image",
        resource_id=analysis.id,
        request=request,
    )
    return _file_response(analysis.original_image_key, "image/jpeg", f"posture-{analysis.id}.jpg")


@router.get("/analyses/{analysis_id}/annotated-image")
def annotated_image(
    request: Request, analysis: PostureAnalysis = Depends(get_owned_analysis), db: Session = Depends(get_db)
) -> FileResponse:
    audit.record(
        db,
        "file.view",
        user_id=analysis.user_id,
        resource_type="annotated_image",
        resource_id=analysis.id,
        request=request,
    )
    return _file_response(analysis.annotated_image_key, "image/jpeg", f"posture-{analysis.id}-annotated.jpg")


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    request: Request, analysis: PostureAnalysis = Depends(get_owned_analysis), db: Session = Depends(get_db)
) -> None:
    """Deletes the analysis, its photos and its report."""
    analysis_service.delete_analysis(db, analysis, request)


@router.get("/progress", response_model=ProgressOut)
def progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProgressOut:
    return analysis_service.progress_for_user(db, user.id)
