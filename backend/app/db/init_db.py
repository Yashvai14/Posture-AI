"""Startup check: the schema is owned by Alembic, so the app refuses to start on an unmigrated database."""

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Engine

from app.core.config import BACKEND_DIR


class DatabaseNotReadyError(RuntimeError):
    pass


def alembic_config() -> Config:
    config = Config(str(Path(BACKEND_DIR) / "alembic.ini"))
    config.set_main_option("script_location", str(Path(BACKEND_DIR) / "alembic"))
    return config


def check_database_ready(engine: Engine) -> None:
    expected = ScriptDirectory.from_config(alembic_config()).get_current_head()
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    if current != expected:
        raise DatabaseNotReadyError(
            f"Database schema is at revision {current!r}, expected {expected!r}. "
            "Run `alembic upgrade head` in the backend directory."
        )
