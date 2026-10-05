from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Shelf(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    shelf_id: str
    display_name: str
    genre: str
    create_time: datetime
    update_time: datetime
    etag: str


class ShelfFields(BaseModel):
    """Client-writable fields of a shelf (create body, update body)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str
    genre: str


class ShelfPatch(BaseModel):
    """Update input; None means "not sent". Only fields in the update mask are applied."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str | None
    genre: str | None
