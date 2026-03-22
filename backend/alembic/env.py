import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Load .env before importing app config
from dotenv import load_dotenv
load_dotenv()

from app.database import Base
import app.models  # noqa: F401 — registers all models with metadata

config = context.config

# Override sqlalchemy.url with DATABASE_URL env var if set
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Escape % for configparser interpolation (e.g. URL-encoded passwords like %40)
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine
    url = database_url or config.get_main_option("sqlalchemy.url", "").replace("%%", "%")
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
