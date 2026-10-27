from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all persisted application models."""


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def new_session() -> Session:
    return get_session_factory()()


def get_session() -> Generator[Session, None, None]:
    """Yield one request-scoped database session and always close it."""
    session = new_session()
    try:
        yield session
    finally:
        session.close()


def database_is_ready() -> bool:
    """Return whether PostgreSQL can be reached and required tables exist."""
    required_tables = {"generation_actuals", "generation_forecasts", "data_import_runs"}
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
            rows = connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename = ANY(:table_names)"
                ),
                {"table_names": list(required_tables)},
            )
            return {row[0] for row in rows} == required_tables
    except Exception:
        return False
