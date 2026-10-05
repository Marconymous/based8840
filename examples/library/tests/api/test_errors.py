import pytest
from httpx import AsyncClient

from app.models.api.v1.error import ErrorResponse
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
    assert {violation.field for violation in error.details} == {"body.displayName", "body.genre"}


@pytest.mark.parametrize("path", ["/v1/unknown", "/v1/shelves/Not_Valid"])
async def test_unknown_routes_and_bad_ids_use_aip_shape(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code in {400, 404}
    assert ErrorResponse.model_validate_json(response.content).error.code == response.status_code
