"""Data access. Every function that reads patient data takes the owner's user_id and filters by it,
so callers cannot accidentally load another user's records."""

import uuid
from datetime import UTC, datetime, timedelta

from geoalchemy2 import Geography
from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.models import (
    ACTIVE_APPOINTMENT_STATUSES,
    AnalysisStatus,
    Appointment,
    Doctor,
    PatientProfile,
    PostureAnalysis,
    Provider,
    ProviderSearchArea,
    User,
)

# ---------------------------------------------------------------- users


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_profile(db: Session, user_id: uuid.UUID) -> PatientProfile | None:
    return db.get(PatientProfile, user_id)


# ---------------------------------------------------------------- analyses

_ANALYSIS_DETAIL = (
    selectinload(PostureAnalysis.snapshot),
    selectinload(PostureAnalysis.measurements),
    selectinload(PostureAnalysis.findings),
    selectinload(PostureAnalysis.recommendation),
    selectinload(PostureAnalysis.report),
)


def get_analysis_for_user(db: Session, analysis_id: uuid.UUID, user_id: uuid.UUID) -> PostureAnalysis | None:
    return db.scalar(
        select(PostureAnalysis)
        .where(PostureAnalysis.id == analysis_id, PostureAnalysis.user_id == user_id)
        .options(*_ANALYSIS_DETAIL)
    )


def list_analyses_for_user(
    db: Session, user_id: uuid.UUID, limit: int, offset: int
) -> tuple[list[PostureAnalysis], int]:
    base = select(PostureAnalysis).where(PostureAnalysis.user_id == user_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(
        base.options(selectinload(PostureAnalysis.snapshot), selectinload(PostureAnalysis.findings))
        .order_by(PostureAnalysis.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), total


def completed_analyses_for_progress(db: Session, user_id: uuid.UUID) -> list[PostureAnalysis]:
    return list(
        db.scalars(
            select(PostureAnalysis)
            .where(PostureAnalysis.user_id == user_id, PostureAnalysis.status == AnalysisStatus.COMPLETED)
            .options(selectinload(PostureAnalysis.measurements))
            .order_by(PostureAnalysis.created_at.asc())
        ).all()
    )


def incomplete_analysis_ids(db: Session) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(PostureAnalysis.id).where(
                PostureAnalysis.status.in_([AnalysisStatus.QUEUED, AnalysisStatus.PROCESSING])
            )
        ).all()
    )


# ---------------------------------------------------------------- providers (public reference data)


def geography_point(latitude: float, longitude: float):
    return cast(func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326), Geography(srid=4326))


CATEGORY_FILTERS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # category: (provider types, specialty tags)
    "physiotherapy": (("physiotherapist", "rehabilitation"), ("physiotherapy", "rehabilitation")),
    "orthopaedics": ((), ("orthopaedics", "orthopedics", "orthopaedic_surgery", "sports_medicine")),
    "chiropractic": (("chiropractor",), ("chiropractic",)),
    "hospital": (("hospital",), ()),
    "clinic": (("clinic", "doctor"), ()),
}


def find_fresh_search_area(
    db: Session, latitude: float, longitude: float, radius_m: int, max_age: timedelta
) -> ProviderSearchArea | None:
    """A previously fetched area that fully contains the requested circle and is still fresh."""
    point = geography_point(latitude, longitude)
    return db.scalar(
        select(ProviderSearchArea)
        .where(
            ProviderSearchArea.radius_m >= radius_m,
            ProviderSearchArea.fetched_at > datetime.now(UTC) - max_age,
            func.ST_DWithin(ProviderSearchArea.location, point, ProviderSearchArea.radius_m - radius_m),
        )
        .order_by(ProviderSearchArea.fetched_at.desc())
        .limit(1)
    )


def search_providers(
    db: Session, latitude: float, longitude: float, radius_m: int, category: str | None, limit: int
) -> list[tuple[Provider, float, int]]:
    """Providers within radius, nearest first, with distance (m) and number of bookable doctors."""
    point = geography_point(latitude, longitude)
    distance = func.ST_Distance(Provider.location, point).label("distance_m")
    bookable = (
        select(func.count(Doctor.id))
        .where(Doctor.provider_id == Provider.id, Doctor.is_bookable.is_(True))
        .correlate(Provider)
        .scalar_subquery()
        .label("bookable")
    )
    query = select(Provider, distance, bookable).where(
        Provider.is_active.is_(True), func.ST_DWithin(Provider.location, point, radius_m)
    )
    if category in CATEGORY_FILTERS:
        types, specialties = CATEGORY_FILTERS[category]
        conditions = []
        if types:
            conditions.append(Provider.provider_type.in_(types))
        if specialties:
            conditions.append(Provider.specialties.overlap(list(specialties)))
        query = query.where(or_(*conditions))
    rows = db.execute(query.order_by(distance).limit(limit)).all()
    return [(row[0], float(row[1]), int(row[2])) for row in rows]


def get_provider_with_doctors(db: Session, provider_id: uuid.UUID) -> Provider | None:
    return db.scalar(
        select(Provider)
        .where(Provider.id == provider_id, Provider.is_active.is_(True))
        .options(selectinload(Provider.doctors).selectinload(Doctor.availability))
    )


def get_bookable_doctor(db: Session, doctor_id: uuid.UUID) -> Doctor | None:
    return db.scalar(
        select(Doctor)
        .where(Doctor.id == doctor_id, Doctor.is_bookable.is_(True))
        .options(selectinload(Doctor.availability), selectinload(Doctor.provider))
    )


# ---------------------------------------------------------------- appointments


def get_appointment_for_user(db: Session, appointment_id: uuid.UUID, user_id: uuid.UUID) -> Appointment | None:
    return db.scalar(
        select(Appointment)
        .where(Appointment.id == appointment_id, Appointment.patient_id == user_id)
        .options(selectinload(Appointment.doctor).selectinload(Doctor.provider))
    )


def list_appointments_for_user(db: Session, user_id: uuid.UUID) -> list[Appointment]:
    return list(
        db.scalars(
            select(Appointment)
            .where(Appointment.patient_id == user_id)
            .options(selectinload(Appointment.doctor).selectinload(Doctor.provider))
            .order_by(Appointment.starts_at.desc())
        ).all()
    )


def active_appointments_for_doctor(
    db: Session, doctor_id: uuid.UUID, start: datetime, end: datetime
) -> list[Appointment]:
    return list(
        db.scalars(
            select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
                Appointment.starts_at < end,
                Appointment.ends_at > start,
            )
        ).all()
    )
