import asyncio
from pathlib import Path

from httpx import AsyncClient

from app.models.api.v1.operation import OperationResponse
from tests.helpers import error_status


async def test_export_books_runs_as_long_running_operation(client: AsyncClient) -> None:
    _ = await client.post(
        "/v1/shelves", params={"shelfId": "scifi"}, json={"displayName": "SF", "genre": "sf"}
    )
    _ = await client.post(
        "/v1/shelves/scifi/books", json={"title": "Dune", "author": "Herbert", "description": ""}
    )

    started = OperationResponse.model_validate_json(
        (await client.post("/v1/shelves/scifi:exportBooks")).content
    )
    # ASGITransport waits for background tasks, so the export has finished by now.
    polled = OperationResponse.model_validate_json(
        (await client.get(f"/v1/{started.name}")).content
    )

    assert not started.done
    assert polled.done
    assert polled.error is None
    assert polled.response is not None
    assert polled.response.exported_count == 1
    exported: str = await asyncio.to_thread(Path(polled.response.result_path).read_text)
    assert '"title": "Dune"' in exported


async def test_export_missing_shelf_is_not_found(client: AsyncClient) -> None:
    response = await client.post("/v1/shelves/nope:exportBooks")

    assert response.status_code == 404
    assert error_status(response) == "NOT_FOUND"
