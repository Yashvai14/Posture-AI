import threading
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.core.errors import ConflictError
from app.db.session import SessionLocal
from app.models.models import Appointment, AppointmentStatus, User
from app.schemas.schemas import AppointmentCreate
from app.services import appointments
from tests.helpers import auth_headers

IST = ZoneInfo("Asia/Kolkata")


def slots(client, headers, doctor, day):
    response = client.get(f"/api/doctors/{doctor.id}/slots", params={"date": day.isoformat()}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def book(client, headers, doctor, starts_at, **extra):
    return client.post(
        "/api/appointments", headers=headers, json={"doctor_id": str(doctor.id), "starts_at": starts_at, **extra}
    )


def test_slots_follow_availability_in_clinic_time(client, make_doctor, slot_day):
    headers = auth_headers(client)
    body = slots(client, headers, make_doctor(), slot_day)
    assert body["timezone"] == "Asia/Kolkata"
    assert [s["local_time"] for s in body["slots"]] == [f"{h:02d}:{m:02d}" for h in range(9, 13) for m in (0, 30)]
    first = datetime.fromisoformat(body["slots"][0]["starts_at"])
    assert first == datetime.combine(slot_day, time(9), IST)  # 09:00 IST
    assert first.utcoffset() == timedelta(0)  # returned in UTC


def test_booking_flow_and_double_booking(client, make_doctor, slot_day):
    alice = auth_headers(client, "alice@example.com", "Alice")
    bob = auth_headers(client, "bob@example.com", "Bob")
    doctor = make_doctor()
    target = slots(client, alice, doctor, slot_day)["slots"][2]

    response = book(client, alice, doctor, target["starts_at"], notes="Neck stiffness")
    assert response.status_code == 201, response.text
    appointment = response.json()
    assert appointment["status"] == "pending" and appointment["can_cancel"] is True
    assert (
        appointment["doctor"]["full_name"] == "Dr. Test Doctor"
        and appointment["provider"]["timezone"] == "Asia/Kolkata"
    )

    # The slot disappears for everyone, and a second booking is refused by the database constraint.
    assert target["starts_at"] not in [s["starts_at"] for s in slots(client, bob, doctor, slot_day)["slots"]]
    conflict = book(client, bob, doctor, target["starts_at"])
    assert conflict.status_code == 409 and conflict.json()["code"] == "slot_unavailable"

    # Cancelling frees the slot again.
    cancelled = client.post(f"/api/appointments/{appointment['id']}/cancel", headers=alice)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert client.post(f"/api/appointments/{appointment['id']}/cancel", headers=alice).status_code == 409
    assert book(client, bob, doctor, target["starts_at"]).status_code == 201


def test_patient_cannot_be_in_two_places_at_once(client, make_doctor, make_provider, slot_day):
    alice = auth_headers(client)
    first = make_doctor()
    second = make_doctor(provider=make_provider(name="Other Clinic"), name="Dr. Second")
    start = slots(client, alice, first, slot_day)["slots"][0]["starts_at"]
    assert book(client, alice, first, start).status_code == 201
    assert book(client, alice, second, start).status_code == 409


def test_only_real_slots_can_be_booked(client, make_doctor, slot_day, settings):
    headers = auth_headers(client)
    doctor = make_doctor()
    off_grid = datetime.combine(slot_day, time(9, 10), IST).isoformat()
    outside_hours = datetime.combine(slot_day, time(15, 0), IST).isoformat()
    past = datetime.combine(slot_day - timedelta(days=10), time(9, 0), IST).isoformat()
    too_far = datetime.combine(slot_day + timedelta(days=settings.BOOKING_WINDOW_DAYS + 5), time(9, 0), IST).isoformat()
    for starts_at in (off_grid, outside_hours, past, too_far):
        response = book(client, headers, doctor, starts_at)
        assert response.status_code == 422, starts_at
    naive = datetime.combine(slot_day, time(9, 0)).isoformat()
    assert book(client, headers, doctor, naive).status_code == 422


def test_unbookable_doctors_cannot_be_booked(client, make_doctor, slot_day):
    headers = auth_headers(client)
    doctor = make_doctor(bookable=False)
    assert (
        client.get(
            f"/api/doctors/{doctor.id}/slots", params={"date": slot_day.isoformat()}, headers=headers
        ).status_code
        == 404
    )
    start = datetime.combine(slot_day, time(9), IST).isoformat()
    assert book(client, headers, doctor, start).status_code == 404


def test_concurrent_bookings_for_the_same_slot(client, db, make_doctor, slot_day):
    auth_headers(client, "alice@example.com")
    auth_headers(client, "bob@example.com")
    doctor = make_doctor()
    users = db.scalars(select(User)).all()
    start = datetime.combine(slot_day, time(10), IST)
    barrier = threading.Barrier(len(users))
    outcomes = []

    def attempt(user_id):
        with SessionLocal() as session:
            user = session.get(User, user_id)
            barrier.wait()
            try:
                appointments.book(session, user, AppointmentCreate(doctor_id=doctor.id, starts_at=start))
                outcomes.append("booked")
            except ConflictError:
                outcomes.append("conflict")

    threads = [threading.Thread(target=attempt, args=(u.id,)) for u in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["booked", "conflict"]
    assert db.scalar(select(func.count(Appointment.id))) == 1


@pytest.mark.parametrize(
    ("start", "target", "allowed"),
    [
        (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, True),
        (AppointmentStatus.PENDING, AppointmentStatus.COMPLETED, False),
        (AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED, True),
        (AppointmentStatus.CONFIRMED, AppointmentStatus.NO_SHOW, True),
        (AppointmentStatus.CANCELLED, AppointmentStatus.CONFIRMED, False),
        (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, False),
    ],
)
def test_state_machine(start, target, allowed):
    appointment = Appointment(status=start, starts_at=datetime.now(UTC) + timedelta(days=1))
    if allowed:
        appointments.transition(appointment, target)
        assert appointment.status == target
    else:
        with pytest.raises(ConflictError):
            appointments.transition(appointment, target)
