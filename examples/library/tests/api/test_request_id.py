import re

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.request_context import REQUEST_ID


async def _current_request_id() -> dict[str, str]:
    return {"requestId": REQUEST_ID.get()}


@pytest.fixture
async def id_client(app: FastAPI) -> AsyncClient:
    # Echoes the ContextVar the log formatters read, so tests see what log lines would carry.
    app.add_api_route("/request-id", _current_request_id)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_request_id_from_client_is_kept_and_echoed(id_client: AsyncClient) -> None:
    async with id_client:
        response = await id_client.get("/request-id", headers={"X-Request-Id": "abc-123"})

    assert response.headers["X-Request-Id"] == "abc-123"
    assert response.json() == {"requestId": "abc-123"}


@pytest.mark.parametrize("header", [{}, {"X-Request-Id": "bad id\ninjected"}])
async def test_request_id_generated_when_missing_or_unsafe(
    id_client: AsyncClient, header: dict[str, str]
) -> None:
    async with id_client:
        response = await id_client.get("/request-id", headers=header)

    generated = response.headers["X-Request-Id"]
    assert re.fullmatch(r"[0-9a-f]{32}", generated)
    assert response.json() == {"requestId": generated}
