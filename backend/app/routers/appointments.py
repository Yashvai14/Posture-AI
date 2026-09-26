import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.models import Appointment, User
from app.repositories import repository as repo
from app.routers.deps import get_current_user
from app.schemas.schemas import AppointmentCreate, AppointmentOut
from app.services import appointments

router = APIRouter(prefix="/appointments", tags=["appointments"])


def to_out(appointment: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=appointment.id,
        status=appointment.status.value,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
        notes=appointment.notes,
        created_at=appointment.created_at,
        cancelled_at=appointment.cancelled_at,
        analysis_id=appointment.analysis_id,
        doctor=appointment.doctor,
        provider=appointment.doctor.provider,
        can_cancel=appointments.can_cancel(appointment),
    )


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book(
    data: AppointmentCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AppointmentOut:
    return to_out(appointments.book(db, user, data, request))


@router.get("", response_model=list[AppointmentOut])
def list_mine(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AppointmentOut]:
    return [to_out(a) for a in repo.list_appointments_for_user(db, user.id)]


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(
    appointment_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AppointmentOut:
    appointment = repo.get_appointment_for_user(db, appointment_id, user.id)
    if appointment is None:
        raise NotFoundError("Appointment not found.")
    return to_out(appointments.cancel_by_patient(db, appointment, request))
