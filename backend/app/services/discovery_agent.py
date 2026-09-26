"""Healthcare-provider discovery from OpenStreetMap.

- One Overpass query per area; results are cached in PostgreSQL (provider_search_areas) for PROVIDER_CACHE_DAYS.
- Only fields present in OpenStreetMap are stored. Unnamed features are skipped. Nothing is generated.
- Place search uses Nominatim with a descriptive User-Agent, at most one request per second, and a cache,
  as required by the Nominatim usage policy.
"""

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationFailedError
from app.models.models import Provider, ProviderSearchArea, ProviderSource
from app.repositories import repository as repo

logger = logging.getLogger(__name__)

ATTRIBUTION = "Provider data © OpenStreetMap contributors, available under the Open Database License (ODbL)."
MAX_RESULTS = 100
OVERPASS_ELEMENT_LIMIT = 2000

_SPECIALTY_ALIASES = {"orthopedics": "orthopaedics", "physiotherapist": "physiotherapy"}


class DiscoveryError(Exception):
    pass


@dataclass(frozen=True)
class SearchResult:
    rows: list[tuple[Provider, float, int]]
    status: str
    message: str
    fetched_at: datetime | None


def overpass_query(latitude: float, longitude: float, radius_m: int) -> str:
    around = f"around:{radius_m},{latitude:.6f},{longitude:.6f}"
    return f"""[out:json][timeout:25];
(
  nwr["healthcare"~"^(physiotherapist|doctor|clinic|hospital|rehabilitation|centre)$"]({around});
  nwr["amenity"~"^(hospital|clinic|doctors)$"]({around});
  nwr["healthcare"="alternative"]["healthcare:speciality"~"chiropractic"]({around});
);
out center tags {OVERPASS_ELEMENT_LIMIT};"""


def _provider_type(tags: dict) -> str | None:
    healthcare = tags.get("healthcare", "")
    amenity = tags.get("amenity", "")
    speciality = tags.get("healthcare:speciality", "").lower()
    if healthcare == "physiotherapist" or "physiotherapy" in speciality:
        return "physiotherapist"
    if "chiropractic" in speciality:
        return "chiropractor"
    if healthcare == "rehabilitation" or "rehabilitation" in speciality:
        return "rehabilitation"
    if healthcare == "hospital" or amenity == "hospital":
        return "hospital"
    if healthcare == "doctor" or amenity == "doctors":
        return "doctor"
    if healthcare in ("clinic", "centre") or amenity == "clinic":
        return "clinic"
    return None


def _address(tags: dict) -> str | None:
    if tags.get("addr:full"):
        return tags["addr:full"]
    street = " ".join(p for p in (tags.get("addr:housenumber"), tags.get("addr:street")) if p)
    parts = [
        street,
        tags.get("addr:suburb") or tags.get("addr:neighbourhood"),
        tags.get("addr:city"),
        tags.get("addr:postcode"),
    ]
    joined = ", ".join(p for p in parts if p)
    return joined or None


def _website(tags: dict) -> str | None:
    url = tags.get("website") or tags.get("contact:website")
    return url if url and url.startswith(("http://", "https://")) else None


def _clip(value: str | None, length: int) -> str | None:
    return value[:length] if value else None


def normalize_element(element: dict) -> dict | None:
    """Maps an Overpass element to provider columns, or None when it lacks a name, location or relevant type."""
    tags = element.get("tags") or {}
    name = (tags.get("name:en") or tags.get("name") or "").strip()
    if not name:
        return None
    if "lat" in element and "lon" in element:
        latitude, longitude = element["lat"], element["lon"]
    elif element.get("center"):
        latitude, longitude = element["center"]["lat"], element["center"]["lon"]
    else:
        return None
    provider_type = _provider_type(tags)
    if provider_type is None:
        return None
    specialties = []
    for raw in tags.get("healthcare:speciality", "").split(";"):
        value = _SPECIALTY_ALIASES.get(raw.strip().lower(), raw.strip().lower())
        if value and value not in specialties:
            specialties.append(value[:80])
    if provider_type == "physiotherapist" and "physiotherapy" not in specialties:
        specialties.append("physiotherapy")
    element_ref = f"{element['type']}/{element['id']}"
    return {
        "name": name[:255],
        "provider_type": provider_type,
        "specialties": specialties[:10],
        "address": _address(tags),
        "phone": _clip(tags.get("phone") or tags.get("contact:phone"), 100),
        "email": _clip(tags.get("email") or tags.get("contact:email"), 255),
        "website": _clip(_website(tags), 500),
        "opening_hours": _clip(tags.get("opening_hours"), 500),
        "latitude": float(latitude),
        "longitude": float(longitude),
        "source": ProviderSource.OPENSTREETMAP,
        "source_id": element_ref,
        "source_url": f"https://www.openstreetmap.org/{element_ref}",
    }


def deduplicate(records: list[dict]) -> list[dict]:
    """The same place is often mapped twice (e.g. a node and a building outline). Keep the richer record."""
    best: dict[tuple, dict] = {}
    for record in records:
        key = (
            re.sub(r"[^a-z0-9]", "", record["name"].lower()),
            round(record["latitude"], 3),
            round(record["longitude"], 3),
        )
        richness = sum(1 for k in ("address", "phone", "website", "opening_hours", "email") if record.get(k))
        current = best.get(key)
        if current is None or richness > current[0]:
            best[key] = (richness, record)
    return [record for _, record in best.values()]


def fetch_from_overpass(
    latitude: float, longitude: float, radius_m: int, transport: httpx.BaseTransport | None = None
) -> list[dict]:
    settings = get_settings()
    try:
        with httpx.Client(
            timeout=35.0, transport=transport, headers={"User-Agent": settings.HTTP_USER_AGENT}
        ) as client:
            response = client.post(settings.OVERPASS_URL, data={"data": overpass_query(latitude, longitude, radius_m)})
            response.raise_for_status()
            elements = response.json().get("elements", [])
    except (httpx.HTTPError, ValueError) as exc:
        raise DiscoveryError(f"Overpass request failed: {exc.__class__.__name__}") from exc
    return deduplicate([r for r in (normalize_element(e) for e in elements) if r is not None])


def store_providers(db: Session, records: list[dict]) -> None:
    # ON CONFLICT cannot touch the same row twice in one statement, so keys must be unique within the batch.
    unique = list({r["source_id"]: r for r in records}.values())
    if not unique:
        return
    statement = insert(Provider).values(
        [{"id": uuid.uuid4(), "timezone": get_settings().DEFAULT_TIMEZONE, **r} for r in unique]
    )
    updatable = (
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
        "source_url",
    )
    statement = statement.on_conflict_do_update(
        constraint="uq_providers_source_source_id",
        set_={**{c: statement.excluded[c] for c in updatable}, "fetched_at": func.now(), "is_active": True},
    )
    db.execute(statement)


def search(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float,
    category: str | None,
    transport: httpx.BaseTransport | None = None,
) -> SearchResult:
    settings = get_settings()
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValidationFailedError("Invalid coordinates.")
    if not (0 < radius_km <= settings.MAX_SEARCH_RADIUS_KM):
        raise ValidationFailedError(f"Radius must be between 0 and {settings.MAX_SEARCH_RADIUS_KM:g} km.")
    radius_m = int(radius_km * 1000)

    if not settings.PROVIDER_DISCOVERY_ENABLED:
        status, message, fetched_at = "disabled", "Showing providers already stored in PostureAI.", None
    else:
        area = repo.find_fresh_search_area(
            db, latitude, longitude, radius_m, timedelta(days=settings.PROVIDER_CACHE_DAYS)
        )
        if area is not None:
            status, message, fetched_at = "cached", "Listings from OpenStreetMap (cached).", area.fetched_at
        else:
            try:
                records = fetch_from_overpass(latitude, longitude, radius_m, transport)
                store_providers(db, records)
                area = ProviderSearchArea(
                    latitude=latitude, longitude=longitude, radius_m=radius_m, result_count=len(records)
                )
                db.add(area)
                db.commit()
                status, message, fetched_at = "fresh", "Listings from OpenStreetMap.", datetime.now(UTC)
            except DiscoveryError as exc:
                db.rollback()
                logger.warning("provider discovery failed", extra={"error": str(exc)})
                status = "unavailable"
                message = "OpenStreetMap could not be reached, so only providers already stored are shown."
                fetched_at = None
    rows = repo.search_providers(db, latitude, longitude, radius_m, category, MAX_RESULTS)
    return SearchResult(rows=rows, status=status, message=message, fetched_at=fetched_at)


# ---------------------------------------------------------------- place search (Nominatim)

_geocode_lock = threading.Lock()
_last_geocode = 0.0
_geocode_cache: dict[str, tuple[float, list[dict]]] = {}
GEOCODE_CACHE_SECONDS = 24 * 3600


def geocode(query: str, transport: httpx.BaseTransport | None = None) -> list[dict]:
    global _last_geocode
    settings = get_settings()
    key = " ".join(query.lower().split())
    now = time.monotonic()
    cached = _geocode_cache.get(key)
    if cached and now - cached[0] < GEOCODE_CACHE_SECONDS:
        return cached[1]
    with _geocode_lock:
        wait = 1.0 - (time.monotonic() - _last_geocode)
        if wait > 0:
            time.sleep(wait)
        try:
            with httpx.Client(
                timeout=10.0,
                transport=transport,
                headers={"User-Agent": settings.HTTP_USER_AGENT, "Accept-Language": "en"},
            ) as client:
                response = client.get(
                    f"{settings.NOMINATIM_URL.rstrip('/')}/search", params={"q": query, "format": "jsonv2", "limit": 5}
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DiscoveryError("Place search is unavailable right now.") from exc
        finally:
            _last_geocode = time.monotonic()
    results = [
        {"display_name": item["display_name"], "latitude": float(item["lat"]), "longitude": float(item["lon"])}
        for item in data
        if "lat" in item and "lon" in item
    ]
    if len(_geocode_cache) > 500:
        _geocode_cache.clear()
    _geocode_cache[key] = (now, results)
    return results
