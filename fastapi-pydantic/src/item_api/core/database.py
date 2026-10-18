"""SQLite engine setup."""

import sqlite3

from sqlalchemy import Engine, create_engine, event, make_url
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool


def create_db_engine(url: str) -> Engine:
    """Create a SQLite engine with foreign key enforcement turned on.

    Args:
        url: SQLAlchemy URL, e.g. ``sqlite:///./item_api.db`` or ``sqlite://`` (in-memory).

    Returns:
        The configured engine.
    """
    in_memory = make_url(url).database in (None, "", ":memory:")
    engine = create_engine(
        url,
        # FastAPI runs sync routes and dependencies in a threadpool.
        connect_args={"check_same_thread": False},
        # Each in-memory connection is a separate empty database, so share a single one.
        poolclass=StaticPool if in_memory else None,
    )
    event.listen(engine, "connect", _enable_foreign_keys)
    return engine


def _enable_foreign_keys(dbapi_connection: sqlite3.Connection, _: ConnectionPoolEntry) -> None:
    # SQLite ignores FOREIGN KEY constraints unless this is set on every connection.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()
