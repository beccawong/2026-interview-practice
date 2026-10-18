from datetime import UTC
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from item_api.crud import item as item_crud
from item_api.models.item import Item


def test_save_and_reload_item(db_session: Session) -> None:
    item = item_crud.save_item(db_session, Item(name="Widget", price=Decimal("9.99")))
    db_session.expunge_all()  # force a real reload from the database

    loaded = item_crud.get_item(db_session, item.id)

    assert loaded is not None
    assert loaded.price == Decimal("9.99")
    assert loaded.in_stock is True
    assert loaded.created_at.tzinfo == UTC


def test_save_changed_item_bumps_updated_at(db_session: Session) -> None:
    item = item_crud.save_item(db_session, Item(name="Widget", price=Decimal("9.99")))
    created_at = item.created_at

    item.in_stock = False
    updated = item_crud.save_item(db_session, item)

    assert updated.created_at == created_at
    assert updated.updated_at > created_at


def test_database_enforces_unique_name(db_session: Session) -> None:
    item_crud.save_item(db_session, Item(name="Widget", price=Decimal("1.00")))

    with pytest.raises(IntegrityError):
        item_crud.save_item(db_session, Item(name="Widget", price=Decimal("2.00")))
