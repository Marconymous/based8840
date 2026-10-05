"""SQL DAO for long-running operations."""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.domain.operation import Operation
from app.models.sql.operation import OperationRow


class SqlOperationDao:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def find(self, operation_id: str) -> Operation | None:
        row: OperationRow | None = await self._session.get(OperationRow, operation_id)
        return None if row is None else Operation.model_validate(row, from_attributes=True)

    async def insert(self, operation: Operation) -> Operation:
        self._session.add(_to_row(operation))
        await self._session.flush()
        return operation

    async def update(self, operation: Operation) -> Operation:
        _ = await self._session.merge(_to_row(operation))
        await self._session.flush()
        return operation


def _to_row(operation: Operation) -> OperationRow:
    return OperationRow(
        operation_id=operation.operation_id,
        kind=operation.kind,
        shelf_id=operation.shelf_id,
        done=operation.done,
        result_path=operation.result_path,
        exported_count=operation.exported_count,
        error_message=operation.error_message,
        create_time=operation.create_time,
        update_time=operation.update_time,
    )
