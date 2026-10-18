from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from item_api.models.item import Item


def list_items(session: Session, *, offset: int = 0, limit: int = 100) -> Sequence[Item]:
    query = select(Item).order_by(Item.created_at, Item.id).offset(offset).limit(limit)
    return session.scalars(query).all()


def get_item(session: Session, item_id: UUID) -> Item | None:
    return session.get(Item, item_id)


def get_item_by_name(session: Session, name: str) -> Item | None:
    return session.scalar(select(Item).where(Item.name == name))


def save_item(session: Session, item: Item) -> Item:
    """Insert a new Item or persist changes made to a loaded one."""
    session.add(item)
    session.commit()
    return item


def delete_item(session: Session, item: Item) -> None:
    session.delete(item)
    session.commit()
