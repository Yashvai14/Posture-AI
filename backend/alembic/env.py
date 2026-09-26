from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.models import models  # noqa: F401  (registers tables on Base.metadata)

target_metadata = Base.metadata

# PostGIS creates its own tables and objects; they are not part of our schema.
POSTGIS_TABLES = {"spatial_ref_sys"}


def include_object(obj, name, type_, reflected, compare_to):
    return not (type_ == "table" and name in POSTGIS_TABLES)


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = context.config.attributes.get("database_url") or get_settings().DATABASE_URL
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
