"""Routers for approved exercise library, 30-day posture plans, and daily check-ins."""

import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import (
    DailyCheckin,
    ExerciseLibraryItem,
    PostureAnalysis,
    PostureProgram,
    User,
)
from app.routers.deps import get_current_user
from app.services.recommendations import LIBRARY

router = APIRouter(tags=["programs"])


# ---------------------------------------------------------------- Schemas


class CheckinCreate(BaseModel):
    checkin_date: date = Field(default_factory=date.today)
    neck_discomfort: int = Field(ge=1, le=10)
    shoulder_discomfort: int = Field(ge=1, le=10)
    back_discomfort: int = Field(ge=1, le=10)
    exercises_completed: str = Field(pattern="^(yes|partially|no)$")
    notes: str | None = None


class CheckinOut(BaseModel):
    id: uuid.UUID
    checkin_date: date
    neck_discomfort: int
    shoulder_discomfort: int
    back_discomfort: int
    exercises_completed: str
    notes: str | None
    created_at: datetime


class ExerciseOut(BaseModel):
    id: str
    name: str
    category: str
    description: str
    instructions: str
    target_area: str
    difficulty: str
    duration: str
    repetitions: str
    frequency: str
    safety_notes: str
    target_findings: list[str]


class ProgramGenerateIn(BaseModel):
    analysis_id: uuid.UUID | None = None
    occupation: str | None = "software_developer"
    language: str | None = "en"


class ProgramOut(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID | None
    occupation: str | None
    preferred_language: str
    title: str
    weeks_data: dict[str, Any]
    completed_days: list[str]
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------- Exercise Library Endpoints


@router.get("/exercises", response_model=list[ExerciseOut])
def get_exercises(
    target_area: str | None = None,
    category: str | None = None,
    finding: str | None = None,
    db: Session = Depends(get_db),
) -> list[ExerciseOut]:
    """Returns curated approved exercises from the medical exercise library."""
    # Seed library items if table is empty
    existing = db.execute(select(ExerciseLibraryItem)).scalars().all()
    if not existing:
        for ex in LIBRARY:
            db.add(
                ExerciseLibraryItem(
                    id=ex.id,
                    name=ex.name,
                    category=ex.category,
                    description=f"{ex.name} designed for posture correction and muscle balance.",
                    instructions=ex.instructions,
                    target_area="cervical" if "head" in ex.id or "chin" in ex.id else "thoracic_lumbar",
                    difficulty="beginner",
                    duration=ex.duration,
                    repetitions=ex.duration,
                    frequency=ex.frequency,
                    safety_notes=ex.safety_note,
                    target_findings=list(ex.targets),
                )
            )
        db.commit()
        existing = db.execute(select(ExerciseLibraryItem)).scalars().all()

    items = existing
    if target_area:
        items = [i for i in items if target_area.lower() in i.target_area.lower()]
    if category:
        items = [i for i in items if i.category.lower() == category.lower()]
    if finding:
        items = [i for i in items if "*" in i.target_findings or finding in i.target_findings]

    return [
        ExerciseOut(
            id=i.id,
            name=i.name,
            category=i.category,
            description=i.description,
            instructions=i.instructions,
            target_area=i.target_area,
            difficulty=i.difficulty,
            duration=i.duration,
            repetitions=i.repetitions,
            frequency=i.frequency,
            safety_notes=i.safety_notes,
            target_findings=i.target_findings,
        )
        for i in items
    ]


# ---------------------------------------------------------------- Daily Check-in Endpoints


@router.post("/checkins", response_model=CheckinOut, status_code=status.HTTP_201_CREATED)
def submit_checkin(
    data: CheckinCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckinOut:
    """Submit daily posture symptom tracking and exercise completion."""
    existing = (
        db.execute(
            select(DailyCheckin).where(
                DailyCheckin.user_id == user.id,
                DailyCheckin.checkin_date == data.checkin_date,
            )
        )
        .scalars()
        .first()
    )
    if existing:
        existing.neck_discomfort = data.neck_discomfort
        existing.shoulder_discomfort = data.shoulder_discomfort
        existing.back_discomfort = data.back_discomfort
        existing.exercises_completed = data.exercises_completed
        existing.notes = data.notes
        db.commit()
        db.refresh(existing)
        return CheckinOut(
            id=existing.id,
            checkin_date=existing.checkin_date,
            neck_discomfort=existing.neck_discomfort,
            shoulder_discomfort=existing.shoulder_discomfort,
            back_discomfort=existing.back_discomfort,
            exercises_completed=existing.exercises_completed,
            notes=existing.notes,
            created_at=existing.created_at,
        )

    checkin = DailyCheckin(
        user_id=user.id,
        checkin_date=data.checkin_date,
        neck_discomfort=data.neck_discomfort,
        shoulder_discomfort=data.shoulder_discomfort,
        back_discomfort=data.back_discomfort,
        exercises_completed=data.exercises_completed,
        notes=data.notes,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return CheckinOut(
        id=checkin.id,
        checkin_date=checkin.checkin_date,
        neck_discomfort=checkin.neck_discomfort,
        shoulder_discomfort=checkin.shoulder_discomfort,
        back_discomfort=checkin.back_discomfort,
        exercises_completed=checkin.exercises_completed,
        notes=checkin.notes,
        created_at=checkin.created_at,
    )


@router.get("/checkins", response_model=list[CheckinOut])
def get_checkins(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CheckinOut]:
    """Retrieve user's historical daily check-ins."""
    records = (
        db.execute(
            select(DailyCheckin)
            .where(DailyCheckin.user_id == user.id)
            .order_by(desc(DailyCheckin.checkin_date))
            .limit(days)
        )
        .scalars()
        .all()
    )
    return [
        CheckinOut(
            id=r.id,
            checkin_date=r.checkin_date,
            neck_discomfort=r.neck_discomfort,
            shoulder_discomfort=r.shoulder_discomfort,
            back_discomfort=r.back_discomfort,
            exercises_completed=r.exercises_completed,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in records
    ]


# ---------------------------------------------------------------- 30-Day Posture Programs


@router.post("/programs/generate", response_model=ProgramOut)
def generate_posture_program(
    payload: ProgramGenerateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramOut:
    """Generates an evidence-aligned 30-day progressive posture plan based on findings and occupation."""
    # Find relevant findings
    finding_codes: list[str] = []
    if payload.analysis_id:
        analysis = db.get(PostureAnalysis, payload.analysis_id)
        if analysis and analysis.user_id == user.id:
            finding_codes = [f.code for f in analysis.findings]

    occ = payload.occupation or (user.profile.occupation if user.profile else "office_worker") or "office_worker"
    lang = payload.language or (user.profile.preferred_language if user.profile else "en") or "en"

    # Select targeted exercises
    targeted_ex = [
        {"id": ex.id, "name": ex.name, "category": ex.category, "instructions": ex.instructions, "duration": ex.duration}
        for ex in LIBRARY
        if "*" in ex.targets or any(fc in ex.targets for fc in finding_codes)
    ]
    if not targeted_ex:
        targeted_ex = [
            {"id": ex.id, "name": ex.name, "category": ex.category, "instructions": ex.instructions, "duration": ex.duration}
            for ex in LIBRARY[:3]
        ]

    weeks_data = {
        "week_1": {
            "title": "Week 1: Postural Awareness & Gentle Mobility",
            "focus": "Establish daily posture checks and reset neck/shoulder tightness.",
            "exercises": targeted_ex[:2],
            "frequency": "Daily, 5-8 minutes",
        },
        "week_2": {
            "title": "Week 2: Mobility & Muscle Activation",
            "focus": "Expand active range of motion and activate postural stabilizer muscles.",
            "exercises": targeted_ex[:3],
            "frequency": "Daily, 8-10 minutes",
        },
        "week_3": {
            "title": "Week 3: Strengthening & Endurance",
            "focus": "Build endurance in scapular retractors, core stabilizers, and deep neck flexors.",
            "exercises": targeted_ex,
            "frequency": "Daily, 10-12 minutes",
        },
        "week_4": {
            "title": "Week 4: Habit Consolidation & Maintenance",
            "focus": "Maintain symmetry and integrate dynamic ergonomic habits into your workday.",
            "exercises": targeted_ex,
            "frequency": "Daily, 10 minutes",
        },
    }

    program = PostureProgram(
        user_id=user.id,
        analysis_id=payload.analysis_id,
        occupation=occ,
        preferred_language=lang,
        title=f"30-Day Posture Alignment Plan ({occ.replace('_', ' ').title()})",
        weeks_data=weeks_data,
        completed_days=[],
    )
    db.add(program)
    db.commit()
    db.refresh(program)

    return ProgramOut(
        id=program.id,
        analysis_id=program.analysis_id,
        occupation=program.occupation,
        preferred_language=program.preferred_language,
        title=program.title,
        weeks_data=program.weeks_data,
        completed_days=program.completed_days,
        is_active=program.is_active,
        created_at=program.created_at,
    )


@router.get("/programs/active", response_model=ProgramOut | None)
def get_active_program(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramOut | None:
    """Retrieve the user's latest active 30-day program."""
    prog = (
        db.execute(
            select(PostureProgram)
            .where(PostureProgram.user_id == user.id, PostureProgram.is_active.is_(True))
            .order_by(desc(PostureProgram.created_at))
        )
        .scalars()
        .first()
    )
    if not prog:
        return None
    return ProgramOut(
        id=prog.id,
        analysis_id=prog.analysis_id,
        occupation=prog.occupation,
        preferred_language=prog.preferred_language,
        title=prog.title,
        weeks_data=prog.weeks_data,
        completed_days=prog.completed_days,
        is_active=prog.is_active,
        created_at=prog.created_at,
    )


@router.post("/programs/{program_id}/complete-day")
def mark_program_day_completed(
    program_id: uuid.UUID,
    day_str: str = Query(..., description="e.g. Day 1, Day 2"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Mark a day completed on the 30-day plan."""
    prog = db.get(PostureProgram, program_id)
    if not prog or prog.user_id != user.id:
        raise HTTPException(status_code=404, detail="Program not found")

    days = list(prog.completed_days)
    if day_str not in days:
        days.append(day_str)
        prog.completed_days = days
        db.commit()

    return {"status": "ok", "completed_days": prog.completed_days, "total_completed": len(prog.completed_days)}
