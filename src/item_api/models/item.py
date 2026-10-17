from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Numeric, String, true
from sqlalchemy.orm import Mapped, mapped_column

from item_api.models.base import Base, UTCDateTime, utcnow


class Item(Base):
    """The Item entity and the ``items`` table."""

    __tablename__ = "items"
    __table_args__ = (CheckConstraint("price > 0", name="ck_items_price_positive"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(1000))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    in_stock: Mapped[bool] = mapped_column(server_default=true())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
