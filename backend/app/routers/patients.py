from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import PatientProfile, User
from app.repositories import repository as repo
from app.routers.deps import get_current_user
from app.routers.analysis import build_legacy_analysis_dict
from app.schemas.schemas import ProfileIn, ProfileOut

router = APIRouter(tags=["patients"])


@router.get("/patients/me/profile", response_model=ProfileOut)
def read_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProfileOut:
    profile = repo.get_profile(db, user.id)
    return ProfileOut.model_validate(profile) if profile else ProfileOut()


@router.put("/patients/me/profile", response_model=ProfileOut)
def update_profile(
    data: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PatientProfile:
    profile = repo.get_profile(db, user.id) or PatientProfile(user_id=user.id)
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    db.add(profile)
    db.commit()
    return profile


@router.get("/patients/history")
def get_patient_history(
    search: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analyses, _ = repo.list_analyses_for_user(db, user.id, limit=50, offset=0)
    history = []
    for a in analyses:
        snapshot = a.snapshot
        patient_name = snapshot.full_name if snapshot else user.full_name
        symptoms = snapshot.symptoms if snapshot else ""

        if search:
            query = search.strip().lower()
            if query not in patient_name.lower() and query not in symptoms.lower():
                continue

        legacy = build_legacy_analysis_dict(a, db)
        history.append({
            "analysis_id": str(a.id),
            "patient_name": patient_name,
            "risk_level": legacy["risk_level"],
            "created_at": a.created_at.isoformat(),
            "age": snapshot.age if snapshot else None,
            "gender": snapshot.sex.capitalize() if (snapshot and snapshot.sex) else "Unspecified",
            "height": float(snapshot.height_cm) if (snapshot and snapshot.height_cm) else None,
            "weight": float(snapshot.weight_kg) if (snapshot and snapshot.weight_kg) else None,
            "symptoms": symptoms,
            "detected_problems": legacy["detected_problems"],
            "report_id": legacy["report_id"],
        })
    return history

