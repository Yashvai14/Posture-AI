"""One user must never be able to see, download, modify or link another user's health data."""

import uuid

import pytest

from tests.helpers import auth_headers, upload


@pytest.fixture
def alice_and_bob(client):
    alice = auth_headers(client, "alice@example.com", "Alice Example")
    bob = auth_headers(client, "bob@example.com", "Bob Example")
    response = upload(client, alice, symptoms="Neck stiffness after long desk days", sex="female")
    assert response.status_code == 202, response.text
    analysis_id = response.json()["id"]
    assert client.get(f"/api/analyses/{analysis_id}", headers=alice).json()["status"] == "completed"
    return alice, bob, analysis_id


@pytest.mark.parametrize("suffix", ["", "/image", "/annotated-image", "/report"])
def test_other_users_analysis_resources_are_not_found(client, alice_and_bob, suffix):
    alice, bob, analysis_id = alice_and_bob
    assert client.get(f"/api/analyses/{analysis_id}{suffix}", headers=alice).status_code == 200
    response = client.get(f"/api/analyses/{analysis_id}{suffix}", headers=bob)
    assert response.status_code == 404
    assert "Neck stiffness" not in response.text


def test_other_user_cannot_delete(client, alice_and_bob):
    alice, bob, analysis_id = alice_and_bob
    assert client.delete(f"/api/analyses/{analysis_id}", headers=bob).status_code == 404
    assert client.get(f"/api/analyses/{analysis_id}", headers=alice).status_code == 200


def test_lists_and_progress_only_contain_own_records(client, alice_and_bob):
    alice, bob, analysis_id = alice_and_bob
    assert client.get("/api/analyses", headers=bob).json() == {"items": [], "total": 0}
    progress = client.get("/api/progress", headers=bob).json()
    assert progress["side"] == [] and progress["frontal"] == []
    assert [a["id"] for a in client.get("/api/analyses", headers=alice).json()["items"]] == [analysis_id]


def test_profile_is_private(client, alice_and_bob):
    alice, bob, _ = alice_and_bob
    assert client.get("/api/patients/me/profile", headers=alice).json()["sex"] == "female"
    assert client.get("/api/patients/me/profile", headers=bob).json()["sex"] is None


def test_cannot_attach_someone_elses_analysis_to_a_booking(client, alice_and_bob, make_doctor, slot_day):
    alice, bob, analysis_id = alice_and_bob
    doctor = make_doctor()
    slot = client.get(f"/api/doctors/{doctor.id}/slots", params={"date": slot_day.isoformat()}, headers=bob).json()[
        "slots"
    ][0]
    response = client.post(
        "/api/appointments",
        headers=bob,
        json={"doctor_id": str(doctor.id), "starts_at": slot["starts_at"], "analysis_id": analysis_id},
    )
    assert response.status_code == 404


def test_appointments_are_private(client, alice_and_bob, make_doctor, slot_day):
    alice, bob, _ = alice_and_bob
    doctor = make_doctor()
    slot = client.get(f"/api/doctors/{doctor.id}/slots", params={"date": slot_day.isoformat()}, headers=alice).json()[
        "slots"
    ][0]
    booked = client.post(
        "/api/appointments", headers=alice, json={"doctor_id": str(doctor.id), "starts_at": slot["starts_at"]}
    )
    assert booked.status_code == 201
    appointment_id = booked.json()["id"]
    assert client.get("/api/appointments", headers=bob).json() == []
    assert client.post(f"/api/appointments/{appointment_id}/cancel", headers=bob).status_code == 404
    assert client.get("/api/appointments", headers=alice).json()[0]["status"] == "pending"


PROTECTED = [
    ("get", "/api/auth/me"),
    ("get", "/api/patients/me/profile"),
    ("put", "/api/patients/me/profile"),
    ("get", "/api/analyses"),
    ("post", "/api/analyses"),
    ("get", f"/api/analyses/{uuid.uuid4()}"),
    ("get", f"/api/analyses/{uuid.uuid4()}/image"),
    ("get", f"/api/analyses/{uuid.uuid4()}/annotated-image"),
    ("get", f"/api/analyses/{uuid.uuid4()}/report"),
    ("delete", f"/api/analyses/{uuid.uuid4()}"),
    ("get", "/api/progress"),
    ("get", "/api/providers/search?latitude=21.1&longitude=79.1"),
    ("get", f"/api/providers/{uuid.uuid4()}"),
    ("get", f"/api/doctors/{uuid.uuid4()}/slots?date=2030-01-01"),
    ("get", "/api/locations/search?q=Nagpur"),
    ("get", "/api/appointments"),
    ("post", "/api/appointments"),
    ("post", f"/api/appointments/{uuid.uuid4()}/cancel"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_protected_endpoints_require_authentication(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_uploads_are_not_served_as_static_files(client, alice_and_bob):
    assert client.get("/static/uploads/").status_code == 404
    assert client.get("/storage/originals/").status_code == 404


def test_storage_keys_cannot_escape_the_storage_directory():
    from app.services.storage import get_storage

    for key in ("../secret.jpg", "originals/../../x.jpg", "/etc/passwd", "originals/abc.exe"):
        with pytest.raises(ValueError):
            get_storage().path(key)
