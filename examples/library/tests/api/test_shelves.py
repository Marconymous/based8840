from httpx import AsyncClient

from app.models.api.v1.shelf import ListShelvesResponse, ShelfResponse
from tests.helpers import error_status, json_object


async def create_shelf(client: AsyncClient, shelf_id: str) -> ShelfResponse:
    response = await client.post(
        "/v1/shelves",
        params={"shelfId": shelf_id},
        json={"displayName": shelf_id.title(), "genre": "fiction"},
    )
    assert response.status_code == 200
    return ShelfResponse.model_validate_json(response.content)


async def test_create_returns_camel_case_resource(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/shelves", params={"shelfId": "fantasy"}, json={"displayName": "Fantasy", "genre": "f"}
    )

    body: dict[str, object] = json_object(response)
    assert body["name"] == "shelves/fantasy"
    assert set(body) == {"name", "displayName", "genre", "createTime", "updateTime", "etag"}
    assert str(body["createTime"]).endswith("Z")


async def test_create_without_id_generates_one(client: AsyncClient) -> None:
    response = await client.post("/v1/shelves", json={"displayName": "Misc", "genre": "misc"})

    assert ShelfResponse.model_validate_json(response.content).name.startswith("shelves/shelf-")


async def test_create_duplicate_is_already_exists(client: AsyncClient) -> None:
    _ = await create_shelf(client, "fantasy")

    response = await client.post(
        "/v1/shelves", params={"shelfId": "fantasy"}, json={"displayName": "x", "genre": "x"}
    )

    assert response.status_code == 409
    assert error_status(response) == "ALREADY_EXISTS"


async def test_list_paginates_with_opaque_token(client: AsyncClient) -> None:
    for shelf_id in ["a", "b", "c"]:
        _ = await create_shelf(client, shelf_id)

    first = ListShelvesResponse.model_validate_json(
        (await client.get("/v1/shelves", params={"pageSize": 2})).content
    )
    second = ListShelvesResponse.model_validate_json(
        (await client.get("/v1/shelves", params={"pageToken": first.next_page_token})).content
    )

    assert [shelf.name for shelf in first.shelves] == ["shelves/a", "shelves/b"]
    assert [shelf.name for shelf in second.shelves] == ["shelves/c"]
    assert second.next_page_token == ""


async def test_update_with_mask_changes_only_masked_fields(client: AsyncClient) -> None:
    shelf: ShelfResponse = await create_shelf(client, "fantasy")

    response = await client.patch(
        "/v1/shelves/fantasy",
        params={"updateMask": "genre", "etag": shelf.etag},
        json={"displayName": "ignored", "genre": "high fantasy"},
    )

    updated = ShelfResponse.model_validate_json(response.content)
    assert updated.genre == "high fantasy"
    assert updated.display_name == "Fantasy"


async def test_update_with_stale_etag_is_aborted(client: AsyncClient) -> None:
    _ = await create_shelf(client, "fantasy")

    response = await client.patch(
        "/v1/shelves/fantasy", params={"etag": "stale"}, json={"genre": "x"}
    )

    assert response.status_code == 409
    assert error_status(response) == "ABORTED"


async def test_delete_returns_empty_body(client: AsyncClient) -> None:
    _ = await create_shelf(client, "fantasy")

    response = await client.delete("/v1/shelves/fantasy")

    assert response.status_code == 200
    assert json_object(response) == {}
    assert (await client.get("/v1/shelves/fantasy")).status_code == 404


async def test_delete_shelf_with_books_is_failed_precondition(client: AsyncClient) -> None:
    _ = await create_shelf(client, "fantasy")
    _ = await client.post(
        "/v1/shelves/fantasy/books", json={"title": "t", "author": "a", "description": ""}
    )

    response = await client.delete("/v1/shelves/fantasy")

    assert response.status_code == 400
    assert error_status(response) == "FAILED_PRECONDITION"
