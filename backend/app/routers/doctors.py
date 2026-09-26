import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.rate_limit import geocode_limiter
from app.db.session import get_db
from app.models.models import Provider, User
from app.repositories import repository as repo
from app.routers.deps import get_current_user
from app.schemas.schemas import (
    DaySlotsOut,
    DiscoveryStatus,
    GeocodeResult,
    ProviderDetailOut,
    ProviderOut,
    ProviderSearchOut,
    SlotOut,
)
from app.services import appointments, discovery_agent

router = APIRouter(tags=["providers"])

Category = Literal["all", "physiotherapy", "orthopaedics", "chiropractic", "hospital", "clinic"]


def _provider_out(provider: Provider, distance_m: float | None = None, bookable: int = 0) -> dict:
    return {
        **{
            c: getattr(provider, c)
            for c in (
                "id",
                "name",
                "provider_type",
                "specialties",
                "address",
                "phone",
                "email",
                "website",
                "opening_hours",
                "latitude",
                "longitude",
                "timezone",
                "source_url",
                "fetched_at",
                "last_verified_at",
            )
        },
        "source": provider.source.value,
        "distance_km": round(distance_m / 1000, 2) if distance_m is not None else None,
        "bookable_doctors": bookable,
    }


@router.get("/providers/search", response_model=ProviderSearchOut)
def search_providers(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float | None = Query(None, gt=0),
    category: Category = "all",
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProviderSearchOut:
    radius = radius_km or get_settings().DEFAULT_SEARCH_RADIUS_KM
    result = discovery_agent.search(db, latitude, longitude, radius, None if category == "all" else category)
    return ProviderSearchOut(
        providers=[ProviderOut(**_provider_out(p, d, b)) for p, d, b in result.rows],
        discovery=DiscoveryStatus(status=result.status, message=result.message, fetched_at=result.fetched_at),
        attribution=discovery_agent.ATTRIBUTION,
        radius_km=radius,
    )


@router.get("/providers/{provider_id}", response_model=ProviderDetailOut)
def provider_detail(
    provider_id: uuid.UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProviderDetailOut:
    provider = repo.get_provider_with_doctors(db, provider_id)
    if provider is None:
        raise NotFoundError("Provider not found.")
    doctors = list(provider.doctors)
    return ProviderDetailOut(
        **_provider_out(provider, bookable=sum(1 for d in doctors if d.is_bookable)),
        doctors=doctors,
    )


@router.get("/doctors/{doctor_id}/slots", response_model=DaySlotsOut)
def doctor_slots(
    doctor_id: uuid.UUID,
    day: date = Query(..., alias="date"),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DaySlotsOut:
    doctor, slots = appointments.available_slots(db, doctor_id, day)
    return DaySlotsOut(
        doctor_id=doctor.id,
        date=day,
        timezone=doctor.provider.timezone,
        slots=[SlotOut(starts_at=s.starts_at, ends_at=s.ends_at, local_time=s.local_time) for s in slots],
    )


@router.get("/locations/search", response_model=list[GeocodeResult])
def search_locations(
    request: Request,
    q: str = Query(..., min_length=2, max_length=200),
    user: User = Depends(get_current_user),
) -> list[GeocodeResult]:
    """Place search (city, area or address) so users can search without sharing their GPS location."""
    geocode_limiter.check(str(user.id))
    try:
        return [GeocodeResult(**r) for r in discovery_agent.geocode(q)]
    except discovery_agent.DiscoveryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
