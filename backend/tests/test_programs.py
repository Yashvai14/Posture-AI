"""Tests for exercise library, 30-day posture programs, and daily check-ins."""

from datetime import date

import pytest
from tests.helpers import auth_headers


def test_get_exercise_library(client):
    headers = auth_headers(client)
    res = client.get("/api/exercises", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 5
    names = [e["name"] for e in data]
    assert any("Chin" in n for n in names)


def test_daily_checkin_lifecycle(client):
    headers = auth_headers(client)
    payload = {
        "checkin_date": str(date.today()),
        "neck_discomfort": 3,
        "shoulder_discomfort": 4,
        "back_discomfort": 2,
        "exercises_completed": "yes",
        "notes": "Felt good after chin tucks.",
    }
    create_res = client.post("/api/checkins", json=payload, headers=headers)
    assert create_res.status_code == 201
    checkin_data = create_res.json()
    assert checkin_data["neck_discomfort"] == 3
    assert checkin_data["exercises_completed"] == "yes"

    # Fetch checkins list
    list_res = client.get("/api/checkins", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_generate_and_track_30_day_program(client):
    headers = auth_headers(client)
    payload = {
        "occupation": "software_developer",
        "language": "en",
    }
    res = client.post("/api/programs/generate", json=payload, headers=headers)
    assert res.status_code == 200
    prog = res.json()
    assert "week_1" in prog["weeks_data"]
    assert "week_4" in prog["weeks_data"]
    assert "Software Developer" in prog["title"]

    # Retrieve active program
    active_res = client.get("/api/programs/active", headers=headers)
    assert active_res.status_code == 200
    active_prog = active_res.json()
    assert active_prog["id"] == prog["id"]

    # Mark day 1 completed
    complete_res = client.post(
        f"/api/programs/{prog['id']}/complete-day?day_str=Day 1",
        headers=headers,
    )
    assert complete_res.status_code == 200
    assert "Day 1" in complete_res.json()["completed_days"]
