from collections.abc import Sequence

from sqlmodel import col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.domain.page import Page, PageRequest
from app.models.domain.shelf import Shelf
from app.models.sql.shelf import ShelfRow
from app.storage.daos.base import to_page


class SqlShelfDao:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def find(self, shelf_id: str) -> Shelf | None:
        row: ShelfRow | None = await self._session.get(ShelfRow, shelf_id)
        return None if row is None else Shelf.model_validate(row, from_attributes=True)

    async def list_page(self, page: PageRequest) -> Page[Shelf]:
        statement = (
            select(ShelfRow)
            .order_by(col(ShelfRow.create_time), col(ShelfRow.shelf_id))
            .offset(page.offset)
            .limit(page.limit + 1)
        )
        rows: Sequence[ShelfRow] = (await self._session.exec(statement)).all()
        shelves: list[Shelf] = [Shelf.model_validate(row, from_attributes=True) for row in rows]
        return to_page(rows=shelves, page=page)

    async def insert(self, shelf: Shelf) -> Shelf:
        self._session.add(_to_row(shelf))
        await self._session.flush()
        return shelf

    async def update(self, shelf: Shelf) -> Shelf:
        _ = await self._session.merge(_to_row(shelf))
        await self._session.flush()
        return shelf

    async def delete(self, shelf_id: str) -> None:
        _ = await self._session.exec(delete(ShelfRow).where(col(ShelfRow.shelf_id) == shelf_id))


def _to_row(shelf: Shelf) -> ShelfRow:
    return ShelfRow(
        shelf_id=shelf.shelf_id,
        display_name=shelf.display_name,
        genre=shelf.genre,
        create_time=shelf.create_time,
        update_time=shelf.update_time,
        etag=shelf.etag,
    )
