"""Work that runs after the response is sent (BackgroundTasks).

The request's session is already committed and closed by then, so each task opens its own
transaction with session_scope and wires its services by hand.
"""

import logging
from datetime import timedelta
from typing import Final

from app.api.dependencies import AppResources
from app.core.settings import LibrarySettings
from app.models.domain.book import Book
from app.models.domain.operation import ExportResult, Operation
from app.services.books import BookService
from app.services.operations import OperationService
from app.storage.daos.impl.books import SqlBookDao
from app.storage.daos.impl.operations import SqlOperationDao
from app.storage.daos.impl.shelves import SqlShelfDao
from app.storage.db.session import session_scope

logger: Final = logging.getLogger(__name__)


async def run_export(*, resources: AppResources, operation_id: str) -> None:
    library_settings: LibrarySettings = resources.config.settings.library
    async with session_scope(resources.session_factory) as session:
        shelf_dao = SqlShelfDao(session)
        operation_service = OperationService(
            dao=SqlOperationDao(session),
            shelf_dao=shelf_dao,
            export_dir=library_settings.export_dir,
        )
        book_service = BookService(
            dao=SqlBookDao(session),
            shelf_dao=shelf_dao,
            loan_duration=timedelta(days=library_settings.loan_days),
        )
        operation: Operation = await operation_service.get(operation_id)
        books: list[Book] = await book_service.list_for_export(operation.shelf_id)
        try:
            result: ExportResult = await operation_service.write_export(
                operation=operation, books=books
            )
        except OSError as e:
            logger.exception("Export %s failed", operation_id)
            _ = await operation_service.fail(operation=operation, message=f"Export failed: {e}")
            return
        _ = await operation_service.complete(operation=operation, result=result)
