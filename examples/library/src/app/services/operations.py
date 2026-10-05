"""Business logic for long-running operations."""

import asyncio
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from app.core.clock import utc_now
from app.core.errors import NotFoundError
from app.core.ids import new_resource_id, operation_name, shelf_name
from app.models.domain.book import Book
from app.models.domain.operation import ExportResult, Operation, OperationKind
from app.storage.daos.base import OperationDao, ShelfDao


class OperationService:
    def __init__(self, *, dao: OperationDao, shelf_dao: ShelfDao, export_dir: Path) -> None:
        self._dao: OperationDao = dao
        self._shelf_dao: ShelfDao = shelf_dao
        self._export_dir: Path = export_dir

    async def get(self, operation_id: str) -> Operation:
        operation: Operation | None = await self._dao.find(operation_id)
        if operation is None:
            raise NotFoundError(f"Operation '{operation_name(operation_id)}' not found.")
        return operation

    async def start_export(self, shelf_id: str) -> Operation:
        """Records a pending export. The caller schedules the actual work."""
        if await self._shelf_dao.find(shelf_id) is None:
            raise NotFoundError(f"Shelf '{shelf_name(shelf_id)}' not found.")
        now: datetime = utc_now()
        operation = Operation(
            operation_id=new_resource_id(prefix="export"),
            kind=OperationKind.EXPORT_BOOKS,
            shelf_id=shelf_id,
            done=False,
            result_path=None,
            exported_count=None,
            error_message=None,
            create_time=now,
            update_time=now,
        )
        return await self._dao.insert(operation)

    async def write_export(self, *, operation: Operation, books: Sequence[Book]) -> ExportResult:
        path: Path = self._export_dir / f"{operation.operation_id}.json"
        content: str = json.dumps([book.model_dump(mode="json") for book in books], indent=2)
        await asyncio.to_thread(_write_text, path=path, content=content)
        return ExportResult(result_path=str(path), exported_count=len(books))

    async def complete(self, *, operation: Operation, result: ExportResult) -> Operation:
        done: Operation = operation.model_copy(
            update={
                "done": True,
                "result_path": result.result_path,
                "exported_count": result.exported_count,
                "update_time": utc_now(),
            }
        )
        return await self._dao.update(done)

    async def fail(self, *, operation: Operation, message: str) -> Operation:
        failed: Operation = operation.model_copy(
            update={"done": True, "error_message": message, "update_time": utc_now()}
        )
        return await self._dao.update(failed)


def _write_text(*, path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")
