"""FastAPI dependency providers. The only place routes obtain services from."""

from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from item_api.services.item import ItemService


def get_session(request: Request) -> Iterator[Session]:
    session_factory = cast(sessionmaker[Session], request.app.state.session_factory)
    with session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_item_service(session: SessionDep) -> ItemService:
    return ItemService(session)


ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
