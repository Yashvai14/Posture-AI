"""Creates posture analyses and processes them in the background.

Processing is idempotent: each stage replaces its own rows, so an interrupted job can simply be re-run.
"""

import logging
import uuid
from datetime import UTC, date, datetime

from fastapi import Request
from PIL import Image
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.db.session import SessionLocal
from app.models.models import (
    AIRecommendation,
    AnalysisStatus,
    ExplanationSource,
    PatientProfile,
    PatientSnapshot,
    PostureAnalysis,
    PostureFinding,
    PostureMeasurement,
    PostureReport,
    PostureView,
    User,
)
from app.posture.annotator import annotate
from app.posture.classifier import PIPELINE_VERSION
from app.posture.metrics import METRIC_LABELS
from app.repositories import repository as repo
from app.schemas.schemas import AnalysisCreate, AnalysisOut, ProgressOut, ProgressPoint
from app.services import audit, cv_engine
from app.services.image_validation import ValidatedImage
from app.services.jobs import get_job_runner
from app.services.ollama_service import explain
from app.services.pdf_generator import ReportData, build_report
from app.services.recommendations import build_corrective_plan
from app.services.storage import get_storage

logger = logging.getLogger(__name__)

STAGES = (
    ("queued", "Waiting to start"),
    ("checking_image", "Checking image quality"),
    ("detecting_landmarks", "Detecting body landmarks"),
    ("measuring", "Calculating posture measurements"),
    ("explaining", "Generating explanation"),
    ("creating_report", "Creating report"),
)
_STAGE_KEYS = [key for key, _ in STAGES]


def _age_on(birth: date | None, on: date) -> int | None:
    if birth is None:
        return None
    return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))


def create_analysis(
    db: Session, user: User, image: ValidatedImage, data: AnalysisCreate, request: Request | None
) -> PostureAnalysis:
    storage = get_storage()
    key = storage.save("originals", image.jpeg_bytes, ".jpg")
    analysis = PostureAnalysis(
        user_id=user.id,
        status=AnalysisStatus.QUEUED,
        stage="queued",
        original_image_key=key,
        image_width=image.width,
        image_height=image.height,
        image_sha256=image.sha256,
    )
    analysis.snapshot = PatientSnapshot(
        full_name=user.full_name,
        age=_age_on(data.date_of_birth, date.today()),
        sex=data.sex,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        symptoms=data.symptoms,
    )
    if data.save_to_profile:
        profile = db.get(PatientProfile, user.id) or PatientProfile(user_id=user.id)
        for field in ("date_of_birth", "sex", "height_cm", "weight_kg"):
            value = getattr(data, field)
            if value is not None:
                setattr(profile, field, value)
        db.add(profile)
    db.add(analysis)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(key)
        raise
    audit.record(
        db, "analysis.create", user_id=user.id, resource_type="analysis", resource_id=analysis.id, request=request
    )
    get_job_runner().submit(process_analysis, analysis.id)
    return analysis


def _set_stage(db: Session, analysis: PostureAnalysis, stage: str) -> None:
    analysis.stage = stage
    db.commit()


def process_analysis(analysis_id: uuid.UUID) -> None:
    with SessionLocal() as db:
        analysis = db.get(PostureAnalysis, analysis_id)
        if analysis is None or analysis.status in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED):
            return
        analysis.status = AnalysisStatus.PROCESSING
        analysis.started_at = datetime.now(UTC)
        analysis.failure_code = analysis.failure_message = None
        _set_stage(db, analysis, "checking_image")
        try:
            _run_pipeline(db, analysis)
        except Exception:
            logger.exception("analysis processing failed", extra={"analysis_id": str(analysis_id)})
            db.rollback()
            analysis = db.get(PostureAnalysis, analysis_id)
            analysis.status = AnalysisStatus.FAILED
            analysis.failure_code = "processing_error"
            analysis.failure_message = "Something went wrong while analysing this photo. Please try again."
            analysis.completed_at = datetime.now(UTC)
            db.commit()


def _run_pipeline(db: Session, analysis: PostureAnalysis) -> None:
    storage = get_storage()
    with Image.open(storage.path(analysis.original_image_key)) as stored:
        image = stored.convert("RGB")

    _set_stage(db, analysis, "detecting_landmarks")
    result = cv_engine.analyze(image)
    analysis.quality_checks = [c.to_dict() for c in result.quality_checks]
    if result.image_quality:
        analysis.quality_checks.append({
            "code": "quality_scores",
            "passed": True,
            "message": "Detailed image quality metrics",
            "scores": result.image_quality.to_dict(),
        })
    if result.confidence_report:
        analysis.quality_checks.append({
            "code": "confidence_report",
            "passed": True,
            "message": "Measurement confidence report",
            "scores": result.confidence_report.to_dict(),
        })
    if result.analysis_scope:
        analysis.quality_checks.append({
            "code": "analysis_scope",
            "passed": True,
            "message": f"Analysis scope: {result.analysis_scope}",
            "scope": result.analysis_scope,
            "body_region": result.body_region,
            "limitations": result.limitations,
        })
    analysis.pose_model = cv_engine.get_detector().model_name
    analysis.pipeline_version = PIPELINE_VERSION
    if not result.usable:
        analysis.status = AnalysisStatus.FAILED
        analysis.failure_code = "image_unsuitable"
        analysis.failure_message = result.failure_message
        analysis.completed_at = datetime.now(UTC)
        db.commit()
        return

    _set_stage(db, analysis, "measuring")
    old_annotated = analysis.annotated_image_key
    analysis.annotated_image_key = storage.save("annotated", annotate(image, result), ".jpg")
    storage.delete(old_annotated)
    analysis.view = PostureView(result.view.value)
    analysis.alignment_score = result.alignment_score
    analysis.unavailable_metrics = [u.to_dict() for u in result.unavailable]
    db.execute(delete(PostureMeasurement).where(PostureMeasurement.analysis_id == analysis.id))
    db.execute(delete(PostureFinding).where(PostureFinding.analysis_id == analysis.id))
    db.add_all(PostureMeasurement(analysis_id=analysis.id, **m.to_dict()) for m in result.measurements)
    db.add_all(PostureFinding(analysis_id=analysis.id, **f.to_dict()) for f in result.findings)
    analysis.stage = "explaining"
    db.commit()

    occupation = None
    preferred_language = "en"
    if analysis.snapshot:
        occupation = analysis.snapshot.occupation
        preferred_language = analysis.snapshot.preferred_language or "en"
    if not occupation:
        user = db.get(User, analysis.user_id)
        if user and user.profile:
            occupation = user.profile.occupation
            if user.profile.preferred_language:
                preferred_language = user.profile.preferred_language

    snapshot = analysis.snapshot
    plan = build_corrective_plan([f.code for f in result.findings], snapshot.symptoms)
    explanation = explain(
        snapshot={
            "age": snapshot.age,
            "sex": snapshot.sex,
            "height_cm": float(snapshot.height_cm) if snapshot.height_cm is not None else None,
            "weight_kg": float(snapshot.weight_kg) if snapshot.weight_kg is not None else None,
            "symptoms": snapshot.symptoms,
            "occupation": occupation,
            "preferred_language": preferred_language,
        },
        view=result.view.value,
        measurements=[m.to_dict() for m in result.measurements],
        findings=[f.to_dict() for f in result.findings],
        score=result.alignment_score,
        plan=plan,
        occupation=occupation,
        language=preferred_language,
    )
    db.execute(delete(AIRecommendation).where(AIRecommendation.analysis_id == analysis.id))
    db.add(
        AIRecommendation(
            analysis_id=analysis.id,
            source=ExplanationSource(explanation.source),
            model=explanation.model,
            explanation=explanation.explanation.model_dump(),
            corrective_plan=plan,
        )
    )
    analysis.stage = "creating_report"
    db.commit()

    try:
        db.refresh(analysis)
        ensure_report(db, analysis)
    except Exception:
        # Results are valid without the PDF; it is regenerated on first download.
        logger.exception("report generation failed", extra={"analysis_id": str(analysis.id)})
        db.rollback()
    analysis.status = AnalysisStatus.COMPLETED
    analysis.stage = "completed"
    analysis.completed_at = datetime.now(UTC)
    db.commit()


def ensure_report(db: Session, analysis: PostureAnalysis) -> PostureReport:
    """Returns the stored report, generating it if it is missing."""
    storage = get_storage()
    if analysis.report is not None and storage.exists(analysis.report.storage_key):
        return analysis.report
    recommendation = analysis.recommendation
    if recommendation is None or analysis.view is None:
        raise NotFoundError("A report is only available for completed analyses.")
    data = ReportData(
        analysis_id=str(analysis.id),
        created_at=analysis.created_at,
        timezone=get_settings().DEFAULT_TIMEZONE,
        snapshot={
            "full_name": analysis.snapshot.full_name,
            "age": analysis.snapshot.age,
            "sex": analysis.snapshot.sex,
            "height_cm": analysis.snapshot.height_cm,
            "weight_kg": analysis.snapshot.weight_kg,
            "symptoms": analysis.snapshot.symptoms,
            "occupation": analysis.snapshot.occupation if analysis.snapshot else None,
        },
        view=analysis.view.value,
        alignment_score=analysis.alignment_score,
        measurements=[_measurement_dict(m) for m in analysis.measurements],
        unavailable=analysis.unavailable_metrics,
        findings=[_finding_dict(f) for f in analysis.findings],
        explanation=recommendation.explanation,
        explanation_source=recommendation.source.value,
        explanation_model=recommendation.model,
        plan=recommendation.corrective_plan,
        annotated_jpeg=storage.read(analysis.annotated_image_key)
        if storage.exists(analysis.annotated_image_key)
        else None,
        quality_checks=analysis.quality_checks,
    )
    pdf = build_report(data)
    key = storage.save("reports", pdf, ".pdf")
    if analysis.report is not None:
        storage.delete(analysis.report.storage_key)
        analysis.report.storage_key = key
        analysis.report.file_size = len(pdf)
    else:
        analysis.report = PostureReport(storage_key=key, file_size=len(pdf))
    db.commit()
    return analysis.report


def delete_analysis(db: Session, analysis: PostureAnalysis, request: Request | None) -> None:
    storage = get_storage()
    keys = [
        analysis.original_image_key,
        analysis.annotated_image_key,
        analysis.report.storage_key if analysis.report else None,
    ]
    user_id, analysis_id = analysis.user_id, analysis.id
    db.delete(analysis)
    db.commit()
    for key in keys:
        storage.delete(key)
    audit.record(
        db, "analysis.delete", user_id=user_id, resource_type="analysis", resource_id=analysis_id, request=request
    )


def resubmit_incomplete_analyses() -> int:
    """Called at startup: jobs that were queued or interrupted are processed again."""
    with SessionLocal() as db:
        ids = repo.incomplete_analysis_ids(db)
        for analysis in (db.get(PostureAnalysis, i) for i in ids):
            analysis.status = AnalysisStatus.QUEUED
        db.commit()
    for analysis_id in ids:
        get_job_runner().submit(process_analysis, analysis_id)
    return len(ids)


# ---------------------------------------------------------------- serialisation


def _measurement_dict(m: PostureMeasurement) -> dict:
    return {"metric": m.metric, "value": m.value, "unit": m.unit, "confidence": m.confidence, "details": m.details}


def _finding_dict(f: PostureFinding) -> dict:
    return {
        "code": f.code,
        "title": f.title,
        "severity": f.severity.value,
        "metric": f.metric,
        "value": f.value,
        "confidence": f.confidence,
        "observation": f.observation,
    }


def _stages(analysis: PostureAnalysis) -> list[dict]:
    if analysis.status == AnalysisStatus.COMPLETED:
        current = len(_STAGE_KEYS)
    else:
        current = _STAGE_KEYS.index(analysis.stage) if analysis.stage in _STAGE_KEYS else 0
    stages = []
    for index, (key, label) in enumerate(STAGES[1:], start=1):
        if analysis.status == AnalysisStatus.FAILED and index == max(current, 1):
            state = "failed"
        elif index < current or analysis.status == AnalysisStatus.COMPLETED:
            state = "done"
        elif index == current and analysis.status == AnalysisStatus.PROCESSING:
            state = "active"
        else:
            state = "pending"
        stages.append({"key": key, "label": label, "state": state})
    return stages


def to_out(analysis: PostureAnalysis) -> AnalysisOut:
    recommendation = analysis.recommendation
    storage = get_storage()
    return AnalysisOut(
        id=analysis.id,
        status=analysis.status.value,
        stage=analysis.stage,
        stages=_stages(analysis),
        failure_code=analysis.failure_code,
        failure_message=analysis.failure_message,
        view=analysis.view.value if analysis.view else None,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        alignment_score=analysis.alignment_score,
        pipeline_version=analysis.pipeline_version,
        quality_checks=analysis.quality_checks,
        measurements=[
            {**_measurement_dict(m), "label": METRIC_LABELS.get(m.metric, m.metric)} for m in analysis.measurements
        ],
        unavailable_metrics=[
            {**u, "label": METRIC_LABELS.get(u["metric"], u["metric"])} for u in analysis.unavailable_metrics
        ],
        findings=[_finding_dict(f) for f in analysis.findings],
        snapshot=analysis.snapshot,
        explanation=(
            {
                "source": recommendation.source.value,
                "model": recommendation.model,
                "content": recommendation.explanation,
            }
            if recommendation
            else None
        ),
        corrective_plan=recommendation.corrective_plan if recommendation else None,
        has_annotated_image=storage.exists(analysis.annotated_image_key),
        has_report=analysis.status == AnalysisStatus.COMPLETED,
    )


def progress_for_user(db: Session, user_id: uuid.UUID) -> ProgressOut:
    side, frontal = [], []
    for analysis in repo.completed_analyses_for_progress(db, user_id):
        point = ProgressPoint(
            analysis_id=analysis.id,
            created_at=analysis.created_at,
            alignment_score=analysis.alignment_score,
            metrics={m.metric: m.value for m in analysis.measurements},
        )
        (side if analysis.view in (PostureView.LEFT_SIDE, PostureView.RIGHT_SIDE) else frontal).append(point)
    return ProgressOut(side=side, frontal=frontal, metric_labels=METRIC_LABELS)


def compare_analyses(
    db: Session, user_id: uuid.UUID, baseline_id: uuid.UUID, current_id: uuid.UUID
) -> dict:
    from app.core.errors import NotFoundError

    baseline = repo.get_analysis_for_user(db, baseline_id, user_id)
    current = repo.get_analysis_for_user(db, current_id, user_id)

    if not baseline or not current:
        raise NotFoundError("One or both analyses not found for comparison.")

    score_delta = None
    if baseline.alignment_score is not None and current.alignment_score is not None:
        score_delta = round(current.alignment_score - baseline.alignment_score, 1)

    base_m = {m.metric: m for m in baseline.measurements}
    curr_m = {m.metric: m for m in current.measurements}

    deltas = []
    common_keys = set(base_m.keys()) & set(curr_m.keys())
    for k in sorted(common_keys):
        b_val = base_m[k].value
        c_val = curr_m[k].value
        d = round(c_val - b_val, 1)
        desc = (
            f"Measured {abs(d):.1f}° reduction"
            if d < 0
            else (f"Measured {abs(d):.1f}° increase" if d > 0 else "Measurements remained stable")
        )
        deltas.append(
            {
                "metric": k,
                "label": METRIC_LABELS.get(k, k),
                "baseline_value": b_val,
                "current_value": c_val,
                "delta": d,
                "unit": curr_m[k].unit,
                "change_description": desc,
            }
        )

    summary = (
        "Your posture measurements changed between these assessments. "
        "Continue your personalized plan and ergonomic workstation habits to support consistent alignment."
    )

    return {
        "baseline_id": baseline.id,
        "baseline_date": baseline.created_at,
        "current_id": current.id,
        "current_date": current.created_at,
        "baseline_score": baseline.alignment_score,
        "current_score": current.alignment_score,
        "score_delta": score_delta,
        "deltas": deltas,
        "summary_message": summary,
    }


def generate_weekly_summary(db: Session, user_id: uuid.UUID) -> dict:
    from datetime import date, timedelta
    from app.models.models import DailyCheckin, User

    user = db.get(User, user_id)
    today = date.today()
    start_week = today - timedelta(days=7)

    checkins = (
        db.execute(
            select(DailyCheckin).where(
                DailyCheckin.user_id == user_id,
                DailyCheckin.checkin_date >= start_week,
            )
        )
        .scalars()
        .all()
    )

    completed_count = sum(1 for c in checkins if c.exercises_completed in ("yes", "partially"))
    neck_days = sum(1 for c in checkins if c.neck_discomfort >= 4)
    shoulder_days = sum(1 for c in checkins if c.shoulder_discomfort >= 4)
    back_days = sum(1 for c in checkins if c.back_discomfort >= 4)

    occ = (user.profile.occupation if user and user.profile else "prolonged seated work") or "prolonged seated work"
    activity_name = occ.replace("_", " ").title()

    trend = "consistent and stable" if completed_count >= 4 else "progressing with room for regularity"
    focus_areas = [
        "Hourly movement breaks and posture resets",
        "Targeted approved mobility exercises",
        "Screen elevation and workstation ergonomics",
    ]

    summary_text = (
        f"You completed {completed_count} of 7 planned check-ins this week. "
        f"Your posture consistency is {trend}. "
        f"You reported notable neck discomfort on {neck_days} day(s) and shoulder discomfort on {shoulder_days} day(s). "
        f"Your primary daily activity is {activity_name}. "
        "Focus next week on: movement breaks, approved mobility exercises, and workstation setup."
    )

    return {
        "start_date": start_week,
        "end_date": today,
        "sessions_completed": completed_count,
        "sessions_planned": 7,
        "neck_discomfort_days": neck_days,
        "shoulder_discomfort_days": shoulder_days,
        "back_discomfort_days": back_days,
        "primary_activity": activity_name,
        "alignment_trend": trend,
        "focus_areas": focus_areas,
        "summary_text": summary_text,
    }
