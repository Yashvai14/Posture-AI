import math

import httpx
import pytest
from sqlalchemy import func, select

from app.models.models import Provider, ProviderSearchArea, ProviderSource
from app.services import discovery_agent
from tests.conftest import NAGPUR
from tests.helpers import auth_headers


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def offset(km_north: float, km_east: float = 0.0) -> tuple[float, float]:
    lat = NAGPUR[0] + km_north / 111.32
    lon = NAGPUR[1] + km_east / (111.32 * math.cos(math.radians(NAGPUR[0])))
    return lat, lon


OSM_ELEMENTS = [
    {
        "type": "node",
        "id": 1,
        "lat": 21.15,
        "lon": 79.09,
        "tags": {
            "healthcare": "physiotherapist",
            "name": "Spine Physio Centre",
            "addr:street": "Wardha Road",
            "addr:city": "Nagpur",
            "phone": "+91 712 000 0000",
            "website": "https://example.org",
            "opening_hours": "Mo-Sa 09:00-18:00",
        },
    },
    {
        "type": "way",
        "id": 2,
        "center": {"lat": 21.16, "lon": 79.08},
        "tags": {
            "amenity": "hospital",
            "name": "City General Hospital",
            "healthcare:speciality": "orthopaedics;general",
        },
    },
    {"type": "node", "id": 3, "lat": 21.14, "lon": 79.07, "tags": {"amenity": "clinic"}},  # unnamed → skipped
    {
        "type": "node",
        "id": 4,
        "lat": 21.14,
        "lon": 79.07,
        "tags": {"shop": "chemist", "name": "Pharmacy"},
    },  # not healthcare
    {
        "type": "node",
        "id": 5,
        "lat": 21.1501,
        "lon": 79.0901,
        "tags": {"healthcare": "physiotherapist", "name": "Spine Physio Centre"},
    },
    {
        "type": "node",
        "id": 6,
        "lat": 21.13,
        "lon": 79.10,
        "tags": {
            "healthcare": "alternative",
            "healthcare:speciality": "chiropractic",
            "name": "Align Chiro",
            "website": "javascript:alert(1)",
        },
    },
]


# ---------------------------------------------------------------- normalisation


def test_normalisation_keeps_only_real_named_healthcare_features():
    records = [r for r in (discovery_agent.normalize_element(e) for e in OSM_ELEMENTS) if r]
    names = [r["name"] for r in records]
    assert names == ["Spine Physio Centre", "City General Hospital", "Spine Physio Centre", "Align Chiro"]
    physio = records[0]
    assert physio["provider_type"] == "physiotherapist"
    assert physio["specialties"] == ["physiotherapy"]
    assert physio["address"] == "Wardha Road, Nagpur"
    assert physio["source"] == ProviderSource.OPENSTREETMAP and physio["source_id"] == "node/1"
    assert physio["source_url"] == "https://www.openstreetmap.org/node/1"
    hospital = records[1]
    assert (hospital["latitude"], hospital["longitude"]) == (21.16, 79.08)
    assert hospital["specialties"] == ["orthopaedics", "general"]
    chiro = records[3]
    assert chiro["provider_type"] == "chiropractor" and chiro["website"] is None
    # No invented details anywhere.
    for record in records:
        assert set(record) <= {
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
            "source",
            "source_id",
            "source_url",
        }


def test_deduplication_keeps_the_richer_record():
    records = [r for r in (discovery_agent.normalize_element(e) for e in OSM_ELEMENTS) if r]
    deduped = discovery_agent.deduplicate(records)
    physio = [r for r in deduped if r["name"] == "Spine Physio Centre"]
    assert len(physio) == 1 and physio[0]["source_id"] == "node/1"


# ---------------------------------------------------------------- search


def test_radius_search_orders_by_distance_and_matches_haversine(db, make_provider):
    for name, km in (("Near", 2), ("Middle", 12), ("Far", 45)):
        make_provider(name=name, latitude=offset(km)[0], longitude=offset(km)[1])
    result = discovery_agent.search(db, *NAGPUR, radius_km=30, category=None)
    assert result.status == "disabled"
    assert [p.name for p, _, _ in result.rows] == ["Near", "Middle"]
    for provider, distance_m, _ in result.rows:
        expected = haversine_km(*NAGPUR, provider.latitude, provider.longitude)
        assert distance_m / 1000 == pytest.approx(expected, rel=0.01)


def test_category_filter(db, make_provider):
    make_provider(name="Physio", provider_type="physiotherapist", specialties=("physiotherapy",))
    make_provider(name="Ortho Hospital", provider_type="hospital", specialties=("orthopaedics",))
    make_provider(name="General Clinic", provider_type="clinic", specialties=())

    def names(category):
        return {p.name for p, _, _ in discovery_agent.search(db, *NAGPUR, 30, category).rows}

    assert names("physiotherapy") == {"Physio"}
    assert names("orthopaedics") == {"Ortho Hospital"}
    assert names("hospital") == {"Ortho Hospital"}
    assert names("clinic") == {"General Clinic"}
    assert names(None) == {"Physio", "Ortho Hospital", "General Clinic"}


@pytest.fixture
def discovery_on(settings, monkeypatch):
    monkeypatch.setattr(settings, "PROVIDER_DISCOVERY_ENABLED", True)


def test_discovery_fetches_once_then_uses_the_cache(db, discovery_on):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert "User-Agent" in request.headers and "PostureAI" in request.headers["User-Agent"]
        assert b"around%3A30000" in request.content or b"around:30000" in request.content
        return httpx.Response(200, json={"elements": OSM_ELEMENTS})

    transport = httpx.MockTransport(handler)
    first = discovery_agent.search(db, *NAGPUR, 30, None, transport=transport)
    assert first.status == "fresh"
    assert {p.name for p, _, _ in first.rows} == {"Spine Physio Centre", "City General Hospital", "Align Chiro"}
    assert db.scalar(select(func.count(ProviderSearchArea.id))) == 1

    second = discovery_agent.search(db, *NAGPUR, 10, None, transport=transport)  # inside the fetched area
    assert second.status == "cached"
    assert len(calls) == 1

    # Re-fetching the same OSM elements updates rows instead of duplicating them.
    discovery_agent.store_providers(db, [discovery_agent.normalize_element(OSM_ELEMENTS[0])])
    db.commit()
    assert db.scalar(select(func.count(Provider.id))) == 3


def test_overpass_failure_returns_stored_providers(db, discovery_on, make_provider):
    make_provider(name="Stored Clinic", provider_type="clinic")
    transport = httpx.MockTransport(lambda request: httpx.Response(504, text="Gateway Timeout"))
    result = discovery_agent.search(db, *NAGPUR, 30, None, transport=transport)
    assert result.status == "unavailable"
    assert [p.name for p, _, _ in result.rows] == ["Stored Clinic"]
    assert db.scalar(select(func.count(ProviderSearchArea.id))) == 0  # failure is not cached


def test_invalid_search_parameters(db):
    with pytest.raises(Exception, match="Radius"):
        discovery_agent.search(db, *NAGPUR, 500, None)


def test_search_endpoint(client, make_doctor, make_provider):
    headers = auth_headers(client)
    doctor = make_doctor()
    make_provider(name="Unbookable Hospital", provider_type="hospital", specialties=())
    response = client.get(
        "/api/providers/search", params={"latitude": NAGPUR[0], "longitude": NAGPUR[1]}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert "OpenStreetMap contributors" in body["attribution"]
    assert body["radius_km"] == 30
    by_name = {p["name"]: p for p in body["providers"]}
    assert by_name["Test Physio Clinic"]["bookable_doctors"] == 1
    assert by_name["Unbookable Hospital"]["bookable_doctors"] == 0
    for provider in body["providers"]:
        assert "rating" not in provider and "consultation_fee" not in provider

    detail = client.get(f"/api/providers/{doctor.provider_id}", headers=headers).json()
    assert detail["doctors"][0]["full_name"] == "Dr. Test Doctor"
    assert detail["doctors"][0]["consultation_fee"] == "500.00" and detail["doctors"][0]["currency"] == "INR"
    assert (
        client.get("/api/providers/search", params={"latitude": 200, "longitude": 0}, headers=headers).status_code
        == 422
    )


def test_geocoding_uses_cache_and_identifies_itself(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert "PostureAI" in request.headers["User-Agent"]
        return httpx.Response(
            200, json=[{"display_name": "Nagpur, Maharashtra, India", "lat": "21.1458", "lon": "79.0882"}]
        )

    monkeypatch.setattr(discovery_agent, "_geocode_cache", {})
    transport = httpx.MockTransport(handler)
    first = discovery_agent.geocode("Nagpur", transport=transport)
    second = discovery_agent.geocode("  nagpur ", transport=transport)
    assert (
        first == second == [{"display_name": "Nagpur, Maharashtra, India", "latitude": 21.1458, "longitude": 79.0882}]
    )
    assert len(calls) == 1
