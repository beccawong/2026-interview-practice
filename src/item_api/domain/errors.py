from uuid import UUID


class DomainError(Exception):
    """Base class for all domain errors. The API layer maps these to HTTP responses."""


class NotFoundError(DomainError):
    def __init__(self, entity: str, entity_id: UUID) -> None:
        super().__init__(f"{entity} {entity_id} not found")
        self.entity = entity
        self.entity_id = entity_id


class ConflictError(DomainError):
    """Raised when an operation would violate a uniqueness or state rule."""
