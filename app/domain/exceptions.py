class DomainError(Exception):
    """Base class for business-rule violations."""


class EntityNotFoundError(DomainError):
    def __init__(self, entity: str, entity_id: object) -> None:
        super().__init__(f"{entity} '{entity_id}' not found")
        self.entity = entity
        self.entity_id = entity_id


class ConflictError(DomainError):
    pass


class ValidationError(DomainError):
    pass
