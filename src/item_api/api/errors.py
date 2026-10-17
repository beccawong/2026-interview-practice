"""Translate domain errors into HTTP responses, so inner layers stay HTTP-agnostic."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from item_api.domain.errors import ConflictError, DomainError, NotFoundError

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
}


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    status_code = next(
        (code for error, code in _STATUS_BY_ERROR.items() if isinstance(exc, error)),
        status.HTTP_400_BAD_REQUEST,
    )
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
