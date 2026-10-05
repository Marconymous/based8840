from pydantic import BaseModel, ConfigDict


class Page[T](BaseModel):
    """One page of a List result. The API layer turns `has_more` into a page token."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[T]
    has_more: bool


class PageRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    offset: int
    limit: int
