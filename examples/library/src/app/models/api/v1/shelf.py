"""v1 API schemas for shelves."""

from datetime import datetime
from typing import Self

from pydantic import Field

from app.core.ids import shelf_name
from app.models.api.v1.base import ApiModel
from app.models.domain.shelf import Shelf, ShelfFields, ShelfPatch


class ShelfResponse(ApiModel):
    name: str = Field(description="OUTPUT_ONLY. Resource name `shelves/{shelf}`.")
    display_name: str
    genre: str
    create_time: datetime = Field(description="OUTPUT_ONLY.")
    update_time: datetime = Field(description="OUTPUT_ONLY.")
    etag: str = Field(description="OUTPUT_ONLY. Send back on update/delete (AIP-154).")

    @classmethod
    def from_domain(cls, shelf: Shelf) -> Self:
        return cls(
            name=shelf_name(shelf.shelf_id),
            display_name=shelf.display_name,
            genre=shelf.genre,
            create_time=shelf.create_time,
            update_time=shelf.update_time,
            etag=shelf.etag,
        )


class CreateShelfRequest(ApiModel):
    """Body of CreateShelf. REQUIRED: displayName, genre."""

    display_name: str = Field(min_length=1, description="REQUIRED.")
    genre: str = Field(min_length=1, description="REQUIRED.")

    def to_domain(self) -> ShelfFields:
        return ShelfFields(display_name=self.display_name, genre=self.genre)


class UpdateShelfRequest(ApiModel):
    """Body of UpdateShelf. Only fields named in `updateMask` are applied."""

    display_name: str | None = Field(default=None, min_length=1)
    genre: str | None = Field(default=None, min_length=1)

    def to_domain(self) -> ShelfPatch:
        return ShelfPatch(display_name=self.display_name, genre=self.genre)


class ListShelvesResponse(ApiModel):
    shelves: list[ShelfResponse]
    next_page_token: str = Field(description="Empty when there are no more pages.")
