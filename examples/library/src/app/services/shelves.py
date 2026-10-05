from collections.abc import Set
from datetime import datetime

from app.core.clock import utc_now
from app.core.errors import AlreadyExistsError, FailedPreconditionError, NotFoundError
from app.core.ids import check_etag, new_etag, new_resource_id, shelf_name
from app.core.patch import masked_changes
from app.models.domain.page import Page, PageRequest
from app.models.domain.shelf import Shelf, ShelfFields, ShelfPatch
from app.storage.daos.base import BookDao, ShelfDao


class ShelfService:
    def __init__(self, *, dao: ShelfDao, book_dao: BookDao) -> None:
        self._dao: ShelfDao = dao
        self._book_dao: BookDao = book_dao

    async def get(self, shelf_id: str) -> Shelf:
        shelf: Shelf | None = await self._dao.find(shelf_id)
        if shelf is None:
            raise NotFoundError(f"Shelf '{shelf_name(shelf_id)}' not found.")
        return shelf

    async def list_shelves(self, page: PageRequest) -> Page[Shelf]:
        return await self._dao.list_page(page)

    async def create(self, *, shelf_id: str | None, fields: ShelfFields) -> Shelf:
        resolved_id: str = shelf_id or new_resource_id(prefix="shelf")
        if await self._dao.find(resolved_id) is not None:
            raise AlreadyExistsError(f"Shelf '{shelf_name(resolved_id)}' already exists.")
        now: datetime = utc_now()
        shelf = Shelf(
            shelf_id=resolved_id,
            display_name=fields.display_name,
            genre=fields.genre,
            create_time=now,
            update_time=now,
            etag=new_etag(),
        )
        return await self._dao.insert(shelf)

    async def update(
        self, *, shelf_id: str, patch: ShelfPatch, update_mask: Set[str], etag: str | None
    ) -> Shelf:
        current: Shelf = await self.get(shelf_id)
        check_etag(expected=etag, actual=current.etag, resource_name=shelf_name(shelf_id))
        changes: dict[str, object] = masked_changes(patch=patch, update_mask=update_mask)
        updated: Shelf = current.model_copy(
            update={**changes, "update_time": utc_now(), "etag": new_etag()}
        )
        return await self._dao.update(updated)

    async def delete(self, *, shelf_id: str, etag: str | None) -> None:
        current: Shelf = await self.get(shelf_id)
        check_etag(expected=etag, actual=current.etag, resource_name=shelf_name(shelf_id))
        book_count: int = await self._book_dao.count_in_shelf(shelf_id)
        if book_count > 0:
            raise FailedPreconditionError(
                f"Shelf '{shelf_name(shelf_id)}' still holds {book_count} book(s)."
            )
        await self._dao.delete(shelf_id)
