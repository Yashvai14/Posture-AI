"""Test configuration.

Tests run against a dedicated PostgreSQL database (default: the development DATABASE_URL with the
database name replaced by `postureai_test`, or TEST_DATABASE_URL if set). The schema is created with
the real Alembic migrations, and every test starts from empty tables.
"""

import os
import secrets
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _test_database_url() -> str:
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    base = os.environ.get("DATABASE_URL") or dotenv_values(BACKEND_DIR / ".env").get("DATABASE_URL")
    if not base:
        raise RuntimeError("Set TEST_DATABASE_URL (or DATABASE_URL in backend/.env) to run the tests.")
    return urlunsplit(urlsplit(base)._replace(path="/postureai_test"))


_STORAGE = tempfile.mkdtemp(prefix="postureai-test-storage-")
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": _test_database_url(),
        "SECRET_KEY": "test-" + secrets.token_urlsafe(40),
        "STORAGE_DIR": _STORAGE,
        "JOB_MODE": "inline",
        "OLLAMA_ENABLED": "false",
        "PROVIDER_DISCOVERY_ENABLED": "false",
        "RATE_LIMIT_ENABLED": "false",
    }
)

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.posture.detector import MediaPipePoseDetector  # noqa: E402


@pytest.fixture(scope="session")
def pose_detector():
    model_path = get_settings().POSE_MODEL_PATH
    if not model_path.is_file():
        pytest.skip(f"pose model missing at {model_path}; run scripts/download_models.py")
    detector = MediaPipePoseDetector(model_path)
    yield detector
    detector.close()


@pytest.fixture(scope="session")
def migrated_engine():
    from app.db.init_db import alembic_config
    from app.db.session import engine

    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(migrated_engine):
    from app.db.base import Base
    from app.db.session import SessionLocal

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with migrated_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    from fastapi.testclient import TestClient

    from app.core.rate_limit import geocode_limiter, login_limiter, register_limiter, upload_limiter
    from app.main import app

    for limiter in (login_limiter, register_limiter, upload_limiter, geocode_limiter):
        limiter.reset()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def settings():
    return get_settings()


NAGPUR = (21.1458, 79.0882)


@pytest.fixture
def make_provider(db):
    from app.models.models import Provider, ProviderSource

    def factory(
        name="Test Physio Clinic",
        latitude=NAGPUR[0],
        longitude=NAGPUR[1],
        provider_type="physiotherapist",
        specialties=("physiotherapy",),
        source=ProviderSource.MANUAL,
        source_id=None,
    ):
        provider = Provider(
            name=name,
            provider_type=provider_type,
            specialties=list(specialties),
            latitude=latitude,
            longitude=longitude,
            address="Test address",
            timezone="Asia/Kolkata",
            source=source,
            source_id=source_id or f"test-{name}",
        )
        db.add(provider)
        db.commit()
        return provider

    return factory


@pytest.fixture
def make_doctor(db, make_provider):
    from datetime import time
    from decimal import Decimal

    from app.models.models import Doctor, DoctorAvailability

    def factory(provider=None, name="Dr. Test Doctor", bookable=True):
        doctor = Doctor(
            provider=provider or make_provider(),
            full_name=name,
            specialization="Physiotherapist",
            consultation_fee=Decimal("500.00"),
            is_bookable=bookable,
            availability=[
                DoctorAvailability(weekday=d, start_time=time(9), end_time=time(13), slot_minutes=30) for d in range(7)
            ],
        )
        db.add(doctor)
        db.commit()
        return doctor

    return factory


@pytest.fixture
def slot_day():
    """A local date a few days ahead: inside the booking window and past the minimum lead time."""
    from datetime import date, timedelta

    return date.today() + timedelta(days=3)
