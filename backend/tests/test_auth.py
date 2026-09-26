import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.models.models import AuditLog, User
from tests.helpers import PASSWORD, auth_headers, login, register


def test_register_and_login(client, db):
    response = register(client, "  Alice@Example.COM ", "Alice  Example")
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice Example"
    assert "hashed_password" not in body and "password" not in body

    token = login(client, "ALICE@example.com").json()
    assert token["token_type"] == "bearer" and token["expires_in"] > 0
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "alice@example.com"

    stored = db.scalar(select(User))
    assert stored.hashed_password.startswith("$2") and PASSWORD not in stored.hashed_password
    actions = set(db.scalars(select(AuditLog.action)).all())
    assert {"user.register", "user.login"} <= actions


def test_duplicate_email_is_rejected_case_insensitively(client):
    assert register(client, "bob@example.com").status_code == 201
    assert register(client, "BOB@example.com").status_code == 409


@pytest.mark.parametrize(
    "password",
    ["short", "é" * 37],  # too short; 74 bytes exceeds bcrypt's 72-byte limit
)
def test_password_rules(client, password):
    assert register(client, "carol@example.com", password=password).status_code == 422


def test_wrong_password_and_unknown_user_get_the_same_answer(client, db):
    register(client, "dave@example.com")
    wrong = login(client, "dave@example.com", "not the password")
    unknown = login(client, "nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert db.scalar(select(AuditLog).where(AuditLog.action == "user.login_failed")) is not None


def _token(settings, **overrides) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(uuid.uuid4()), "type": "access", "iat": now, "exp": now + timedelta(minutes=5)} | overrides
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm="HS256")


def test_token_is_only_accepted_from_the_authorization_header(client):
    headers = auth_headers(client)
    token = headers["Authorization"].split()[1]
    assert client.get("/api/auth/me").status_code == 401
    assert client.get(f"/api/auth/me?token={token}").status_code == 401
    assert client.get("/api/auth/me", cookies={"token": token}).status_code == 401
    assert client.get("/api/auth/me", headers=headers).status_code == 200


def test_invalid_tokens_are_rejected(client, db, settings):
    headers = auth_headers(client)
    user_id = str(db.scalar(select(User.id)))
    past = datetime.now(UTC) - timedelta(hours=2)
    bad_tokens = [
        "not-a-jwt",
        _token(settings, sub=user_id, exp=past, iat=past - timedelta(hours=1)),  # expired
        jwt.encode(
            {"sub": user_id, "type": "access", "iat": past, "exp": datetime.now(UTC) + timedelta(hours=1)},
            "a-completely-different-secret-key-of-enough-length",
            algorithm="HS256",
        ),  # wrong key
        _token(settings, sub=user_id, type="refresh"),  # wrong type
        _token(settings),  # unknown user
        jwt.encode({"sub": user_id}, key=None, algorithm="none"),  # unsigned
    ]
    for token in bad_tokens:
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401, token
    assert client.get("/api/auth/me", headers=headers).status_code == 200


def test_login_rate_limit(client, settings, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    register(client, "erin@example.com")
    codes = [login(client, "erin@example.com", "wrong password").status_code for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
