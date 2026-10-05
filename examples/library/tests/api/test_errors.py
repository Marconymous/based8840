import pytest
from httpx import ASGITransport, AsyncClient

from app.core.settings import AppConfig
from app.factory import create_app
from app.models.api.v1.error import DebugInfo, ErrorResponse, FieldViolation
from tests.helpers import json_object


async def test_not_found_body_shape(client: AsyncClient) -> None:
    response = await client.get("/v1/shelves/missing")

    assert response.status_code == 404
    assert json_object(response) == {
        "error": {
            "code": 404,
            "message": "Shelf 'shelves/missing' not found.",
            "status": "NOT_FOUND",
            "details": [],
        }
    }


async def test_validation_error_lists_field_violations(client: AsyncClient) -> None:
    response = await client.post("/v1/shelves", json={"genre": ""})

    error = ErrorResponse.model_validate_json(response.content).error
    assert response.status_code == 400
    assert error.status == "INVALID_ARGUMENT"
    fields = {detail.field for detail in error.details if isinstance(detail, FieldViolation)}
    assert fields == {"body.displayName", "body.genre"}


@pytest.mark.parametrize("path", ["/v1/unknown", "/v1/shelves/Not_Valid"])
async def test_unknown_routes_and_bad_ids_use_aip_shape(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code in {400, 404}
    assert ErrorResponse.model_validate_json(response.content).error.code == response.status_code


async def test_unknown_body_field_is_invalid_argument(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/shelves", json={"displayName": "Fiction", "genre": "novels", "color": "red"}
    )

    error = ErrorResponse.model_validate_json(response.content).error
    assert response.status_code == 400
    assert error.status == "INVALID_ARGUMENT"
    assert {detail.field for detail in error.details if isinstance(detail, FieldViolation)} == {
        "body.color"
    }


async def _raise_unexpected() -> None:
    raise RuntimeError("database exploded")


def _client_with_failing_route(*, config: AppConfig, debug_errors: bool) -> AsyncClient:
    settings = config.settings.model_copy(update={"debug_errors": debug_errors})
    app = create_app(config.model_copy(update={"settings": settings}))
    app.add_api_route("/boom", _raise_unexpected)
    # Starlette re-raises after the 500 handler ran; keep the response instead.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_unexpected_error_with_debug_errors_includes_debug_info(config: AppConfig) -> None:
    async with _client_with_failing_route(config=config, debug_errors=True) as client:
        response = await client.get("/boom")

    error = ErrorResponse.model_validate_json(response.content).error
    assert response.status_code == 500
    assert error.status == "INTERNAL"
    assert len(error.details) == 1
    debug = error.details[0]
    assert isinstance(debug, DebugInfo)
    assert debug.detail == "RuntimeError: database exploded"
    assert any("_raise_unexpected" in entry for entry in debug.stack_entries)


async def test_unexpected_error_without_debug_errors_is_generic(config: AppConfig) -> None:
    async with _client_with_failing_route(config=config, debug_errors=False) as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    assert json_object(response) == {
        "error": {"code": 500, "message": "Internal error.", "status": "INTERNAL", "details": []}
    }
