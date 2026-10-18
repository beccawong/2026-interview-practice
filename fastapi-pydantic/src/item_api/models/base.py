from datetime import UTC, datetime

from sqlalchemy import DateTime, Dialect, TypeDecorator
from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores aware datetimes as naive UTC and loads them back as aware UTC.

    SQLite has no timezone support, so without this, loaded datetimes would be naive.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return value.astimezone(UTC).replace(tzinfo=None) if value is not None else None

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None else None


class Base(DeclarativeBase):
    """Base class for all models. ``Base.metadata`` holds every table."""
