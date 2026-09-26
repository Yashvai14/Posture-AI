"""Administrative commands. Run from the backend directory: `python -m app.cli --help`.

Bookable doctors are onboarded here with details supplied by the clinic; PostureAI never generates them.
"""

import argparse
import re
import sys
import uuid
from datetime import UTC, datetime, time
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import (
    PROVIDER_TYPES,
    Appointment,
    AppointmentStatus,
    Doctor,
    DoctorAvailability,
    Provider,
    ProviderSource,
)
from app.services.appointments import transition

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_AVAILABILITY = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun)\s+(\d{2}:\d{2})-(\d{2}:\d{2})(?:/(\d+))?$")


def parse_availability(value: str) -> DoctorAvailability:
    """'mon 09:00-13:00' or 'mon 09:00-13:00/20' (slot length in minutes, default 30)."""
    match = _AVAILABILITY.match(value.strip().lower())
    if not match:
        raise argparse.ArgumentTypeError(f"invalid availability {value!r}; expected e.g. 'mon 09:00-13:00/30'")
    day, start, end, slot = match.groups()
    rule = DoctorAvailability(
        weekday=WEEKDAYS.index(day),
        start_time=time.fromisoformat(start),
        end_time=time.fromisoformat(end),
        slot_minutes=int(slot or 30),
    )
    if rule.end_time <= rule.start_time:
        raise argparse.ArgumentTypeError(f"end time must be after start time in {value!r}")
    return rule


def create_provider(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        provider = Provider(
            name=args.name,
            provider_type=args.type,
            specialties=args.specialty or [],
            address=args.address,
            phone=args.phone,
            email=args.email,
            website=args.website,
            opening_hours=args.opening_hours,
            latitude=args.lat,
            longitude=args.lon,
            timezone=args.timezone,
            source=ProviderSource.MANUAL,
            source_id=str(uuid.uuid4()),
            last_verified_at=datetime.now(UTC),
        )
        db.add(provider)
        db.commit()
        print(f"Created provider {provider.id} ({provider.name})")


def create_doctor(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        provider = db.get(Provider, uuid.UUID(args.provider_id))
        if provider is None:
            sys.exit(f"Provider {args.provider_id} not found")
        doctor = Doctor(
            provider=provider,
            full_name=args.name,
            specialization=args.specialization,
            qualifications=args.qualifications,
            experience_years=args.experience,
            consultation_fee=Decimal(args.fee) if args.fee is not None else None,
            phone=args.phone,
            email=args.email,
            bio=args.bio,
            is_bookable=bool(args.availability),
            source=ProviderSource.MANUAL,
            last_verified_at=datetime.now(UTC),
            availability=args.availability or [],
        )
        db.add(doctor)
        db.commit()
        state = "bookable" if doctor.is_bookable else "not bookable (no availability given)"
        print(f"Created doctor {doctor.id} ({doctor.full_name}) at {provider.name}, {state}")


def set_appointment_status(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        appointment = db.get(Appointment, uuid.UUID(args.id))
        if appointment is None:
            sys.exit(f"Appointment {args.id} not found")
        transition(appointment, AppointmentStatus(args.status))
        db.commit()
        print(f"Appointment {appointment.id} is now {appointment.status.value}")


def list_providers(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        query = select(Provider).order_by(Provider.name)
        if args.manual:
            query = query.where(Provider.source == ProviderSource.MANUAL)
        for provider in db.scalars(query.limit(args.limit)):
            print(f"{provider.id}  {provider.source.value:13s} {provider.provider_type:15s} {provider.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("create-provider", help="add a clinic or hospital entered by an administrator")
    p.add_argument("--name", required=True)
    p.add_argument("--type", required=True, choices=PROVIDER_TYPES)
    p.add_argument("--lat", required=True, type=float)
    p.add_argument("--lon", required=True, type=float)
    p.add_argument("--address", required=True)
    p.add_argument("--specialty", action="append", help="repeatable, e.g. physiotherapy")
    p.add_argument("--phone")
    p.add_argument("--email")
    p.add_argument("--website")
    p.add_argument("--opening-hours")
    p.add_argument("--timezone", default="Asia/Kolkata")
    p.set_defaults(handler=create_provider)

    d = commands.add_parser("create-doctor", help="onboard a doctor with real availability so patients can book")
    d.add_argument("--provider-id", required=True)
    d.add_argument("--name", required=True)
    d.add_argument("--specialization", required=True)
    d.add_argument("--qualifications")
    d.add_argument("--experience", type=int)
    d.add_argument("--fee", help="consultation fee in INR, e.g. 500")
    d.add_argument("--phone")
    d.add_argument("--email")
    d.add_argument("--bio")
    d.add_argument("--availability", action="append", type=parse_availability, help="repeatable: 'mon 09:00-13:00/30'")
    d.set_defaults(handler=create_doctor)

    s = commands.add_parser("set-appointment-status", help="clinic/admin status change (confirm, complete, no-show)")
    s.add_argument("--id", required=True)
    s.add_argument("--status", required=True, choices=[st.value for st in AppointmentStatus])
    s.set_defaults(handler=set_appointment_status)

    ls = commands.add_parser("list-providers")
    ls.add_argument("--manual", action="store_true", help="only manually onboarded providers")
    ls.add_argument("--limit", type=int, default=50)
    ls.set_defaults(handler=list_providers)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
