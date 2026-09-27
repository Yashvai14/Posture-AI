import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, PayloadTooLargeError
from app.core.rate_limit import upload_limiter
from app.db.session import get_db
from app.models.models import AnalysisStatus, PostureAnalysis, User
from app.repositories import repository as repo
from app.routers.deps import get_current_user
from app.schemas.schemas import (
    AnalysisCreate,
    AnalysisOut,
    AnalysisPage,
    AnalysisSummaryOut,
    ComparisonOut,
    ProgressOut,
    WeeklySummaryOut,
)
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


@router.get("/analyses/compare", response_model=ComparisonOut)
def compare_analyses(
    baseline_id: uuid.UUID = Query(...),
    current_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComparisonOut:
    return analysis_service.compare_analyses(db, user.id, baseline_id, current_id)


@router.get("/analyses/weekly-summary", response_model=WeeklySummaryOut)
def weekly_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklySummaryOut:
    return analysis_service.generate_weekly_summary(db, user.id)


def build_legacy_analysis_dict(analysis: PostureAnalysis, db: Session) -> dict:
    db.refresh(analysis)
    metrics_dict = {
        "ear_shoulder_angle": 0.0,
        "shoulder_tilt": 0.0,
        "hip_alignment": 0.0,
    }
    for m in analysis.measurements:
        metric_key = m.metric.lower()
        if any(k in metric_key for k in ("craniovertebral", "ear", "neck", "head")):
            metrics_dict["ear_shoulder_angle"] = round(float(m.value), 1)
        elif "shoulder" in metric_key:
            metrics_dict["shoulder_tilt"] = round(float(m.value), 1)
        elif "hip" in metric_key:
            metrics_dict["hip_alignment"] = round(float(m.value), 1)

    detected_problems = [f.title for f in analysis.findings]
    if not detected_problems and analysis.status == AnalysisStatus.COMPLETED:
        detected_problems = ["No significant postural deviations detected"]

    risk_level = "Low"
    if analysis.alignment_score is not None:
        if analysis.alignment_score < 60 or any(f.severity == "severe" for f in analysis.findings):
            risk_level = "High"
        elif analysis.alignment_score < 80 or any(f.severity == "moderate" for f in analysis.findings):
            risk_level = "Medium"

    rec = analysis.recommendation
    explanation = rec.explanation if rec and rec.explanation else {}
    corrective = rec.corrective_plan if rec and rec.corrective_plan else {}

    stretches = []
    exercises = []
    for ex in corrective.get("exercises", []):
        cat = ex.get("category", "")
        desc = f"{ex.get('name', 'Exercise')}: {ex.get('instructions', '')}"
        if cat in ("stretch", "mobility"):
            stretches.append(desc)
        else:
            exercises.append(desc)

    lifestyle_tips = explanation.get("lifestyle_tips", [])
    if not lifestyle_tips:
        lifestyle_tips = [
            "Adjust your monitor to eye level to avoid neck strain.",
            "Take a 2-minute posture break every 45 minutes of seated work.",
            "Keep your feet flat on the floor with hips level while seated.",
        ]

    findings_text = explanation.get("summary") or explanation.get("what_this_may_mean") or (
        analysis.findings[0].observation if analysis.findings else "Your posture has been evaluated using computer vision body landmark tracking."
    )

    report_id = str(analysis.report.id) if analysis.report else str(analysis.id)

    iq_score = 0.90
    conf_score = round(float(analysis.alignment_score or 85.0) / 100.0, 2)
    analysis_scope = "full_body"
    limitations = []
    if analysis.quality_checks:
        for qc in analysis.quality_checks:
            if qc.get("code") == "quality_scores" and "scores" in qc:
                iq_score = round(qc["scores"].get("overall_quality", 90) / 100.0, 2)
            elif qc.get("code") == "confidence_report" and "scores" in qc:
                conf_score = round(qc["scores"].get("overall_measurement_confidence", 85) / 100.0, 2)
            elif qc.get("code") == "analysis_scope":
                analysis_scope = qc.get("scope", "full_body")
                limitations = qc.get("limitations", [])

    return {
        "analysis_id": str(analysis.id),
        "id": str(analysis.id),
        "report_id": report_id,
        "risk_level": risk_level,
        "confidence_score": conf_score,
        "image_quality_score": iq_score,
        "analysis_scope": analysis_scope,
        "limitations": limitations,
        "metrics": metrics_dict,
        "detected_problems": detected_problems,
        "findings": findings_text,
        "recommendations": {
            "stretches": stretches or ["Neck lateral flexion stretch: 30 seconds each side", "Chest doorway stretch: 30 seconds"],
            "exercises": exercises or ["Chin tucks: 10 repetitions, 3 sets", "Wall angels: 10 repetitions, 2 sets"],
            "lifestyle_tips": lifestyle_tips,
        },
    }


@router.post("/analysis/upload")
async def upload_analysis_legacy(
    request: Request,
    file: UploadFile = File(None),
    image: UploadFile = File(None),
    side_file: UploadFile = File(None),
    back_file: UploadFile = File(None),
    name: Annotated[str | None, Form()] = None,
    age: Annotated[str | None, Form()] = None,
    gender: Annotated[str | None, Form()] = None,
    height: Annotated[str | None, Form()] = None,
    weight: Annotated[str | None, Form()] = None,
    symptoms: Annotated[str | None, Form()] = None,
    occupation: Annotated[str | None, Form()] = None,
    preferred_language: Annotated[str | None, Form()] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    upload = file or image
    if upload is None:
        raise RequestValidationError([{"loc": ["body", "file"], "msg": "Field required", "type": "missing"}])

    if occupation or preferred_language:
        from app.models.models import PatientProfile
        prof = db.get(PatientProfile, user.id) or PatientProfile(user_id=user.id)
        if occupation:
            prof.occupation = occupation
        if preferred_language:
            prof.preferred_language = preferred_language
        db.add(prof)
        db.commit()

    settings = get_settings()
    upload_limiter.check(str(user.id))
    raw = await read_limited(upload, settings.max_upload_bytes)
    validated = validate_image(raw, upload.filename, upload.content_type, settings.MAX_IMAGE_PIXELS)

    sex_val = gender.lower() if gender else None
    if sex_val not in ("male", "female", "other"):
        sex_val = "other" if sex_val else None

    dob = None
    if age and str(age).isdigit():
        dob = f"{date.today().year - int(age)}-01-01"

    data = AnalysisCreate(
        date_of_birth=dob,
        sex=sex_val,
        height_cm=Decimal(str(height)) if height and str(height).replace(".", "", 1).isdigit() else None,
        weight_kg=Decimal(str(weight)) if weight and str(weight).replace(".", "", 1).isdigit() else None,
        symptoms=symptoms,
        save_to_profile=True,
    )
    analysis = analysis_service.create_analysis(db, user, validated, data, request)
    db.refresh(analysis)

    # Wait for the background worker to finish processing (usually takes ~1-2s)
    import time
    for _ in range(40):
        db.expire_all()
        db.refresh(analysis)
        if analysis.status in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED):
            break
        time.sleep(0.25)

    if analysis.status == AnalysisStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=analysis.failure_message or "Postural analysis could not identify body landmarks. Please upload a clear photo of standing posture.",
        )

    res_dict = build_legacy_analysis_dict(analysis, db)

    # Multi-angle evaluation if additional views were provided
    if side_file or back_file:
        from io import BytesIO
        from PIL import Image
        from app.posture import cv_engine
        from app.posture.fusion import fuse_posture_views

        view_results = []
        # Main upload result
        with Image.open(BytesIO(raw)) as main_img:
            main_res = cv_engine.analyze(main_img.convert("RGB"), allow_partial=True)
            view_label = main_res.view.value if main_res.view else "front"
            view_results.append((view_label, main_res))

        if side_file:
            side_raw = await read_limited(side_file, settings.max_upload_bytes)
            with Image.open(BytesIO(side_raw)) as s_img:
                s_res = cv_engine.analyze(s_img.convert("RGB"), allow_partial=True)
                view_results.append(("side", s_res))

        if back_file:
            back_raw = await read_limited(back_file, settings.max_upload_bytes)
            with Image.open(BytesIO(back_raw)) as b_img:
                b_res = cv_engine.analyze(b_img.convert("RGB"), allow_partial=True)
                view_results.append(("back", b_res))

        multi_assessment = fuse_posture_views(view_results)
        res_dict["multi_angle"] = {
            "enabled": True,
            "views_analyzed": multi_assessment.views_analyzed,
            "fused_findings": [f.to_dict() for f in multi_assessment.fused_findings],
            "inconsistencies": multi_assessment.inconsistencies,
            "limitations": multi_assessment.limitations,
            "overall_score": multi_assessment.overall_alignment_score,
            "summary_message": multi_assessment.summary_message,
        }
    else:
        res_dict["multi_angle"] = {"enabled": False}

    return res_dict


@router.get("/analysis/{analysis_id}")
def get_analysis_legacy(
    analysis_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = repo.get_analysis_for_user(db, analysis_id, user.id)
    if analysis is None:
        raise NotFoundError("Analysis not found.")
    return build_legacy_analysis_dict(analysis, db)

