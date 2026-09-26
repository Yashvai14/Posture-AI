"""Slot generation, booking and appointment state changes.

Double booking is prevented by PostgreSQL exclusion constraints (per doctor and per patient); this module
validates requests and translates constraint violations into a 409 response.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models.models import ACTIVE_APPOINTMENT_STATUSES, Appointment, AppointmentStatus, Doctor, User
from app.repositories import repository as repo
from app.schemas.schemas import AppointmentCreate
from app.services import audit

EXCLUSION_VIOLATION = "23P01"

TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.PENDING: {AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED},
    AppointmentStatus.CONFIRMED: {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW},
}


@dataclass(frozen=True)
class Slot:
    starts_at: datetime  # UTC
    ends_at: datetime
    local_time: str


def _now() -> datetime:
    return datetime.now(UTC)


def generate_slots(
    doctor: Doctor, day: date, now: datetime, booked: list[tuple[datetime, datetime]] = ()
) -> list[Slot]:
    """Bookable slots for one local calendar day: inside availability rules, far enough in the future, and free."""
    settings = get_settings()
    tz = ZoneInfo(doctor.provider.timezone)
    earliest = now + timedelta(minutes=settings.BOOKING_MIN_LEAD_MINUTES)
    latest = now + timedelta(days=settings.BOOKING_WINDOW_DAYS)
    slots = []
    for rule in (r for r in doctor.availability if r.weekday == day.weekday()):
        step = timedelta(minutes=rule.slot_minutes)
        start = datetime.combine(day, rule.start_time, tz)
        end_of_rule = datetime.combine(day, rule.end_time, tz)
        while start + step <= end_of_rule:
            start_utc, end_utc = start.astimezone(UTC), (start + step).astimezone(UTC)
            overlaps = any(b_start < end_utc and b_end > start_utc for b_start, b_end in booked)
            if earliest <= start_utc <= latest and not overlaps:
                slots.append(Slot(start_utc, end_utc, start.strftime("%H:%M")))
            start += step
    return sorted(slots, key=lambda s: s.starts_at)


def _day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tz)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def available_slots(db: Session, doctor_id: uuid.UUID, day: date) -> tuple[Doctor, list[Slot]]:
    doctor = repo.get_bookable_doctor(db, doctor_id)
    if doctor is None:
        raise NotFoundError("This doctor does not take bookings through PostureAI.")
    start, end = _day_bounds(day, ZoneInfo(doctor.provider.timezone))
    booked = [(a.starts_at, a.ends_at) for a in repo.active_appointments_for_doctor(db, doctor.id, start, end)]
    return doctor, generate_slots(doctor, day, _now(), booked)


def book(db: Session, patient: User, data: AppointmentCreate, request: Request | None = None) -> Appointment:
    doctor = repo.get_bookable_doctor(db, data.doctor_id)
    if doctor is None:
        raise NotFoundError("This doctor does not take bookings through PostureAI.")
    if data.analysis_id and repo.get_analysis_for_user(db, data.analysis_id, patient.id) is None:
        raise NotFoundError("Analysis not found.")

    starts_at = data.starts_at.astimezone(UTC)
    local_day = starts_at.astimezone(ZoneInfo(doctor.provider.timezone)).date()
    slot = next((s for s in generate_slots(doctor, local_day, _now()) if s.starts_at == starts_at), None)
    if slot is None:
        raise ValidationFailedError("That time is not one of the doctor's available slots.", code="invalid_slot")

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        analysis_id=data.analysis_id,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        status=AppointmentStatus.PENDING,
        notes=data.notes,
    )
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == EXCLUSION_VIOLATION:
            raise ConflictError(
                "That slot is no longer available, or you already have an appointment at that time.",
                code="slot_unavailable",
            ) from exc
        raise
    audit.record(
        db,
        "appointment.create",
        user_id=patient.id,
        resource_type="appointment",
        resource_id=appointment.id,
        request=request,
    )
    return repo.get_appointment_for_user(db, appointment.id, patient.id)


def transition(appointment: Appointment, new_status: AppointmentStatus, now: datetime | None = None) -> None:
    if new_status not in TRANSITIONS.get(appointment.status, set()):
        raise ConflictError(
            f"An appointment that is {appointment.status.value} cannot be marked {new_status.value}.",
            code="invalid_transition",
        )
    appointment.status = new_status
    if new_status == AppointmentStatus.CANCELLED:
        appointment.cancelled_at = now or _now()


def can_cancel(appointment: Appointment, now: datetime | None = None) -> bool:
    return appointment.status in ACTIVE_APPOINTMENT_STATUSES and appointment.starts_at > (now or _now())


def cancel_by_patient(db: Session, appointment: Appointment, request: Request | None = None) -> Appointment:
    if not can_cancel(appointment):
        raise ConflictError(
            "Only upcoming pending or confirmed appointments can be cancelled.", code="invalid_transition"
        )
    transition(appointment, AppointmentStatus.CANCELLED)
    db.commit()
    audit.record(
        db,
        "appointment.cancel",
        user_id=appointment.patient_id,
        resource_type="appointment",
        resource_id=appointment.id,
        request=request,
    )
    return appointment
