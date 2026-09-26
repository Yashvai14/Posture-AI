from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import PatientProfile, User
from app.repositories import repository as repo
from app.routers.deps import get_current_user
from app.schemas.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/patients/me", tags=["patients"])


@router.get("/profile", response_model=ProfileOut)
def read_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProfileOut:
    profile = repo.get_profile(db, user.id)
    return ProfileOut.model_validate(profile) if profile else ProfileOut()


@router.put("/profile", response_model=ProfileOut)
def update_profile(
    data: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PatientProfile:
    profile = repo.get_profile(db, user.id) or PatientProfile(user_id=user.id)
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    db.add(profile)
    db.commit()
    return profile
