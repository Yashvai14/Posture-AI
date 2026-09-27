import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnalysisStatus(enum.StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PostureView(enum.StrEnum):
    FRONT = "front"
    BACK = "back"
    LEFT_SIDE = "left_side"  # the person's left side faces the camera
    RIGHT_SIDE = "right_side"


class Severity(enum.StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    PRONOUNCED = "pronounced"


class ExplanationSource(enum.StrEnum):
    OLLAMA = "ollama"
    RULE_BASED = "rule_based"


class ProviderSource(enum.StrEnum):
    OPENSTREETMAP = "openstreetmap"
    MANUAL = "manual"


class AppointmentStatus(enum.StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


ACTIVE_APPOINTMENT_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
PROVIDER_TYPES = ("hospital", "clinic", "doctor", "physiotherapist", "chiropractor", "rehabilitation")
SEX_VALUES = ("female", "male", "other", "prefer_not_to_say")


def _enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


def _updated_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


def _geography_point() -> Mapped[Any]:
    return mapped_column(
        Geography("POINT", srid=4326, spatial_index=False),
        Computed("ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography", persisted=True),
    )


# ---------------------------------------------------------------- users & profiles


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    profile: Mapped["PatientProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class PatientProfile(Base):
    """The user's current profile, used to pre-fill new analyses. Historical values live in PatientSnapshot."""

    __tablename__ = "patient_profiles"
    __table_args__ = (
        CheckConstraint(f"sex IN {SEX_VALUES}", name="sex_valid"),
        CheckConstraint("height_cm BETWEEN 50 AND 250", name="height_range"),
        CheckConstraint("weight_kg BETWEEN 10 AND 400", name="weight_range"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    date_of_birth: Mapped[date | None]
    sex: Mapped[str | None] = mapped_column(String(20))
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    occupation: Mapped[str | None] = mapped_column(String(50))
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    updated_at: Mapped[datetime] = _updated_at()

    user: Mapped[User] = relationship(back_populates="profile")


# ---------------------------------------------------------------- posture analyses


class PostureAnalysis(Base):
    __tablename__ = "posture_analyses"
    __table_args__ = (
        CheckConstraint("alignment_score BETWEEN 0 AND 100", name="score_range"),
        Index("ix_posture_analyses_user_created", "user_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[AnalysisStatus] = mapped_column(
        _enum(AnalysisStatus, "analysis_status"), default=AnalysisStatus.QUEUED
    )
    stage: Mapped[str | None] = mapped_column(String(40))
    failure_code: Mapped[str | None] = mapped_column(String(50))
    failure_message: Mapped[str | None] = mapped_column(Text)
    view: Mapped[PostureView | None] = mapped_column(_enum(PostureView, "posture_view"))

    original_image_key: Mapped[str] = mapped_column(String(255))
    annotated_image_key: Mapped[str | None] = mapped_column(String(255))
    image_width: Mapped[int] = mapped_column(Integer)
    image_height: Mapped[int] = mapped_column(Integer)
    image_sha256: Mapped[str] = mapped_column(String(64))

    quality_checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    unavailable_metrics: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    alignment_score: Mapped[float | None] = mapped_column(Float)
    pose_model: Mapped[str | None] = mapped_column(String(100))
    pipeline_version: Mapped[str | None] = mapped_column(String(20))

    created_at: Mapped[datetime] = _created_at()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    snapshot: Mapped["PatientSnapshot"] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", uselist=False
    )
    measurements: Mapped[list["PostureMeasurement"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="PostureMeasurement.metric"
    )
    findings: Mapped[list["PostureFinding"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="PostureFinding.code"
    )
    recommendation: Mapped["AIRecommendation | None"] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", uselist=False
    )
    report: Mapped["PostureReport | None"] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", uselist=False
    )


class PatientSnapshot(Base):
    """Profile and symptoms exactly as entered for one analysis; never updated afterwards."""

    __tablename__ = "patient_snapshots"
    __table_args__ = (
        CheckConstraint("age BETWEEN 0 AND 120", name="age_range"),
        CheckConstraint(f"sex IN {SEX_VALUES}", name="sex_valid"),
        CheckConstraint("height_cm BETWEEN 50 AND 250", name="height_range"),
        CheckConstraint("weight_kg BETWEEN 10 AND 400", name="weight_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posture_analyses.id", ondelete="CASCADE"), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    age: Mapped[int | None] = mapped_column(SmallInteger)
    sex: Mapped[str | None] = mapped_column(String(20))
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    symptoms: Mapped[str | None] = mapped_column(Text)
    occupation: Mapped[str | None] = mapped_column(String(50))
    preferred_language: Mapped[str | None] = mapped_column(String(10), default="en", server_default="en")
    created_at: Mapped[datetime] = _created_at()

    analysis: Mapped[PostureAnalysis] = relationship(back_populates="snapshot")


class PostureMeasurement(Base):
    __tablename__ = "posture_measurements"
    __table_args__ = (
        UniqueConstraint("analysis_id", "metric"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="confidence_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posture_analyses.id", ondelete="CASCADE"))
    metric: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    analysis: Mapped[PostureAnalysis] = relationship(back_populates="measurements")


class PostureFinding(Base):
    __tablename__ = "posture_findings"
    __table_args__ = (
        UniqueConstraint("analysis_id", "code"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="confidence_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posture_analyses.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(120))
    severity: Mapped[Severity] = mapped_column(_enum(Severity, "finding_severity"))
    metric: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    observation: Mapped[str] = mapped_column(Text)

    analysis: Mapped[PostureAnalysis] = relationship(back_populates="findings")


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posture_analyses.id", ondelete="CASCADE"), unique=True)
    source: Mapped[ExplanationSource] = mapped_column(_enum(ExplanationSource, "explanation_source"))
    model: Mapped[str | None] = mapped_column(String(100))
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB)
    corrective_plan: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _created_at()

    analysis: Mapped[PostureAnalysis] = relationship(back_populates="recommendation")


class PostureReport(Base):
    __tablename__ = "posture_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posture_analyses.id", ondelete="CASCADE"), unique=True)
    storage_key: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created_at()

    analysis: Mapped[PostureAnalysis] = relationship(back_populates="report")


# ---------------------------------------------------------------- providers & doctors


class Provider(Base):
    """A healthcare facility or practice. Data comes from an identified source; nothing is generated."""

    __tablename__ = "providers"
    __table_args__ = (
        UniqueConstraint("source", "source_id"),
        CheckConstraint(f"provider_type IN {PROVIDER_TYPES}", name="provider_type_valid"),
        CheckConstraint("latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180", name="coordinates_valid"),
        Index("ix_providers_location", "location", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    provider_type: Mapped[str] = mapped_column(String(40))
    specialties: Mapped[list[str]] = mapped_column(ARRAY(String(80)), default=list, server_default="{}")
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(500))
    opening_hours: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location: Mapped[Any] = _geography_point()
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", server_default="Asia/Kolkata")
    source: Mapped[ProviderSource] = mapped_column(_enum(ProviderSource, "provider_source"))
    source_id: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(500))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    doctors: Mapped[list["Doctor"]] = relationship(back_populates="provider", order_by="Doctor.full_name")


class ProviderSearchArea(Base):
    """Records which areas were fetched from an external source, so repeat searches use the cache."""

    __tablename__ = "provider_search_areas"
    __table_args__ = (Index("ix_provider_search_areas_location", "location", postgresql_using="gist"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location: Mapped[Any] = _geography_point()
    radius_m: Mapped[int] = mapped_column(Integer)
    result_count: Mapped[int] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Doctor(Base):
    """An individual practitioner onboarded with real details. Only these can take bookings."""

    __tablename__ = "doctors"
    __table_args__ = (
        CheckConstraint("experience_years BETWEEN 0 AND 70", name="experience_range"),
        CheckConstraint("consultation_fee >= 0", name="fee_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("providers.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    qualifications: Mapped[str | None] = mapped_column(String(255))
    specialization: Mapped[str] = mapped_column(String(120))
    experience_years: Mapped[int | None] = mapped_column(SmallInteger)
    consultation_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    phone: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)
    is_bookable: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    source: Mapped[ProviderSource] = mapped_column(
        _enum(ProviderSource, "doctor_source"), default=ProviderSource.MANUAL
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    provider: Mapped[Provider] = relationship(back_populates="doctors")
    availability: Mapped[list["DoctorAvailability"]] = relationship(
        back_populates="doctor",
        cascade="all, delete-orphan",
        order_by="(DoctorAvailability.weekday, DoctorAvailability.start_time)",
    )


class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("end_time > start_time", name="time_order"),
        CheckConstraint("slot_minutes BETWEEN 10 AND 120", name="slot_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int] = mapped_column(SmallInteger)  # 0 = Monday
    start_time: Mapped[time]
    end_time: Mapped[time]
    slot_minutes: Mapped[int] = mapped_column(SmallInteger, default=30, server_default="30")

    doctor: Mapped[Doctor] = relationship(back_populates="availability")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="time_order"),
        ExcludeConstraint(
            ("doctor_id", "="),
            (func.tstzrange(text("starts_at"), text("ends_at")), "&&"),
            name="ex_appointments_doctor_overlap",
            using="gist",
            where=text("status IN ('pending', 'confirmed')"),
        ),
        ExcludeConstraint(
            ("patient_id", "="),
            (func.tstzrange(text("starts_at"), text("ends_at")), "&&"),
            name="ex_appointments_patient_overlap",
            using="gist",
            where=text("status IN ('pending', 'confirmed')"),
        ),
        Index("ix_appointments_patient_starts", "patient_id", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id"), index=True)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("posture_analyses.id", ondelete="SET NULL"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AppointmentStatus] = mapped_column(
        _enum(AppointmentStatus, "appointment_status"), default=AppointmentStatus.PENDING
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    doctor: Mapped[Doctor] = relationship()


# ---------------------------------------------------------------- audit


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60))
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = _created_at()


# ---------------------------------------------------------------- posture programs & check-ins


class DailyCheckin(Base):
    __tablename__ = "daily_checkins"
    __table_args__ = (
        Index("ix_daily_checkins_user_date", "user_id", "checkin_date", unique=True),
        CheckConstraint("neck_discomfort BETWEEN 1 AND 10", name="neck_discomfort_range"),
        CheckConstraint("shoulder_discomfort BETWEEN 1 AND 10", name="shoulder_discomfort_range"),
        CheckConstraint("back_discomfort BETWEEN 1 AND 10", name="back_discomfort_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    checkin_date: Mapped[date] = mapped_column(Date, default=date.today)
    neck_discomfort: Mapped[int] = mapped_column(SmallInteger)
    shoulder_discomfort: Mapped[int] = mapped_column(SmallInteger)
    back_discomfort: Mapped[int] = mapped_column(SmallInteger)
    exercises_completed: Mapped[str] = mapped_column(String(20))  # "yes", "partially", "no"
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at()

    user: Mapped[User] = relationship()


class ExerciseLibraryItem(Base):
    __tablename__ = "exercise_library"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(50))  # mobility | stretch | strength | awareness
    description: Mapped[str] = mapped_column(Text)
    instructions: Mapped[str] = mapped_column(Text)
    target_area: Mapped[str] = mapped_column(String(100))
    difficulty: Mapped[str] = mapped_column(String(30))  # beginner | intermediate | advanced
    duration: Mapped[str] = mapped_column(String(50))
    repetitions: Mapped[str] = mapped_column(String(80))
    frequency: Mapped[str] = mapped_column(String(80))
    safety_notes: Mapped[str] = mapped_column(Text)
    target_findings: Mapped[list[str]] = mapped_column(ARRAY(String(50)), server_default="{}")


class PostureProgram(Base):
    __tablename__ = "posture_programs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("posture_analyses.id", ondelete="SET NULL"))
    occupation: Mapped[str | None] = mapped_column(String(50))
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    title: Mapped[str] = mapped_column(String(150))
    weeks_data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    completed_days: Mapped[list[str]] = mapped_column(ARRAY(String(20)), server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()

    user: Mapped[User] = relationship()

