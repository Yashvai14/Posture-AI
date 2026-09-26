import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Sex = Literal["female", "male", "other", "prefer_not_to_say"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth & profile


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("full name is required")
        return value

    @field_validator("password")
    @classmethod
    def bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 (a token type, not a secret)
    expires_in: int


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    created_at: datetime


class ProfileIn(BaseModel):
    date_of_birth: date | None = None
    sex: Sex | None = None
    height_cm: Decimal | None = Field(default=None, ge=50, le=250, decimal_places=1)
    weight_kg: Decimal | None = Field(default=None, ge=10, le=400, decimal_places=1)

    @field_validator("date_of_birth")
    @classmethod
    def plausible_birth_date(cls, value: date | None) -> date | None:
        if value is not None and not (date(1900, 1, 1) <= value <= date.today()):
            raise ValueError("date of birth must be between 1900 and today")
        return value


class ProfileOut(ProfileIn, ORMModel):
    pass


class AnalysisCreate(ProfileIn):
    symptoms: str | None = Field(default=None, max_length=2000)
    save_to_profile: bool = True

    @field_validator("symptoms")
    @classmethod
    def clean_symptoms(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


# ---------------------------------------------------------------- analyses


class QualityCheckOut(BaseModel):
    code: str
    passed: bool
    message: str
    value: float | None = None


class MeasurementOut(ORMModel):
    metric: str
    label: str
    value: float
    unit: str
    confidence: float
    details: dict[str, Any]


class UnavailableMetricOut(BaseModel):
    metric: str
    label: str
    reason: str


class FindingOut(ORMModel):
    code: str
    title: str
    severity: str
    metric: str
    value: float
    confidence: float
    observation: str


class SnapshotOut(ORMModel):
    full_name: str
    age: int | None
    sex: str | None
    height_cm: Decimal | None
    weight_kg: Decimal | None
    symptoms: str | None


class ExplanationOut(BaseModel):
    source: str
    model: str | None
    content: dict[str, Any]


class StageOut(BaseModel):
    key: str
    label: str
    state: Literal["done", "active", "pending", "failed"]


class AnalysisOut(BaseModel):
    id: uuid.UUID
    status: str
    stage: str | None
    stages: list[StageOut]
    failure_code: str | None
    failure_message: str | None
    view: str | None
    created_at: datetime
    completed_at: datetime | None
    alignment_score: float | None
    pipeline_version: str | None
    quality_checks: list[QualityCheckOut]
    measurements: list[MeasurementOut]
    unavailable_metrics: list[UnavailableMetricOut]
    findings: list[FindingOut]
    snapshot: SnapshotOut
    explanation: ExplanationOut | None
    corrective_plan: dict[str, Any] | None
    has_annotated_image: bool
    has_report: bool


class AnalysisSummaryOut(BaseModel):
    id: uuid.UUID
    status: str
    view: str | None
    created_at: datetime
    alignment_score: float | None
    findings: list[FindingOut]
    symptoms: str | None


class AnalysisPage(BaseModel):
    items: list[AnalysisSummaryOut]
    total: int


class ProgressPoint(BaseModel):
    analysis_id: uuid.UUID
    created_at: datetime
    alignment_score: float | None
    metrics: dict[str, float]


class ProgressOut(BaseModel):
    side: list[ProgressPoint]
    frontal: list[ProgressPoint]
    metric_labels: dict[str, str]


# ---------------------------------------------------------------- providers, doctors, appointments


class AvailabilityOut(ORMModel):
    weekday: int
    start_time: time
    end_time: time
    slot_minutes: int


class DoctorOut(ORMModel):
    id: uuid.UUID
    full_name: str
    qualifications: str | None
    specialization: str
    experience_years: int | None
    consultation_fee: Decimal | None
    currency: str
    phone: str | None
    email: str | None
    bio: str | None
    is_bookable: bool
    last_verified_at: datetime | None
    availability: list[AvailabilityOut]


class ProviderOut(BaseModel):
    id: uuid.UUID
    name: str
    provider_type: str
    specialties: list[str]
    address: str | None
    phone: str | None
    email: str | None
    website: str | None
    opening_hours: str | None
    latitude: float
    longitude: float
    distance_km: float | None = None
    timezone: str
    source: str
    source_url: str | None
    fetched_at: datetime
    last_verified_at: datetime | None
    bookable_doctors: int = 0


class ProviderDetailOut(ProviderOut):
    doctors: list[DoctorOut]


class DiscoveryStatus(BaseModel):
    status: Literal["fresh", "cached", "unavailable", "disabled"]
    message: str
    fetched_at: datetime | None = None


class ProviderSearchOut(BaseModel):
    providers: list[ProviderOut]
    discovery: DiscoveryStatus
    attribution: str
    radius_km: float


class GeocodeResult(BaseModel):
    display_name: str
    latitude: float
    longitude: float


class SlotOut(BaseModel):
    starts_at: datetime
    ends_at: datetime
    local_time: str


class DaySlotsOut(BaseModel):
    doctor_id: uuid.UUID
    date: date
    timezone: str
    slots: list[SlotOut]


class AppointmentCreate(BaseModel):
    doctor_id: uuid.UUID
    starts_at: datetime
    analysis_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("starts_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("starts_at must include a timezone offset")
        return value


class AppointmentDoctorOut(ORMModel):
    id: uuid.UUID
    full_name: str
    specialization: str
    consultation_fee: Decimal | None
    currency: str


class AppointmentProviderOut(ORMModel):
    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    timezone: str


class AppointmentOut(BaseModel):
    id: uuid.UUID
    status: str
    starts_at: datetime
    ends_at: datetime
    notes: str | None
    created_at: datetime
    cancelled_at: datetime | None
    analysis_id: uuid.UUID | None
    doctor: AppointmentDoctorOut
    provider: AppointmentProviderOut
    can_cancel: bool
