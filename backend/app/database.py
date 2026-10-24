"""Database engine and session helpers (SQLModel on top of SQLAlchemy)."""
from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from .config import get_settings


@lru_cache
def get_engine() -> Engine:
    url = get_settings().resolved_database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def _add_missing_columns(engine: Engine) -> None:
    """Additive migration: `create_all` never alters existing tables, so add new columns by hand."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                ddl = col.type.compile(dialect=engine.dialect)
                default = ""
                if col.default is not None and getattr(col.default, "is_scalar", False):
                    val = col.default.arg
                    default = f" DEFAULT {int(val) if isinstance(val, bool) else repr(val)}"
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl}{default}'))


def init_db() -> None:
    from . import db_models  # noqa: F401  (register tables)

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _add_missing_columns(engine)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
