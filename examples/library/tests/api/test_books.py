"""API tests for books."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.api.v1.book import BookResponse, ListBooksResponse
from tests.helpers import error_status, json_object


@pytest.fixture
async def shelf(client: AsyncClient) -> str:
    response = await client.post(
        "/v1/shelves", params={"shelfId": "scifi"}, json={"displayName": "Sci-Fi", "genre": "sf"}
    )
    assert response.status_code == 200
    return "scifi"


async def create_book(client: AsyncClient, *, book_id: str, author: str) -> BookResponse:
    response = await client.post(
        "/v1/shelves/scifi/books",
        params={"bookId": book_id},
        json={"title": book_id.title(), "author": author, "description": ""},
    )
    assert response.status_code == 200, response.text
    return BookResponse.model_validate_json(response.content)


@pytest.mark.usefixtures("shelf")
async def test_get_returns_full_resource(client: AsyncClient) -> None:
    _ = await create_book(client, book_id="dune", author="Herbert")

    body = json_object(await client.get("/v1/shelves/scifi/books/dune"))

    assert body["name"] == "shelves/scifi/books/dune"
    assert body["state"] == "AVAILABLE"
    assert body["deleteTime"] is None


@pytest.mark.usefixtures("shelf")
async def test_request_id_makes_create_idempotent(client: AsyncClient) -> None:
    params = {"requestId": str(uuid4())}
    payload = {"title": "Dune", "author": "Herbert", "description": ""}

    first = await client.post("/v1/shelves/scifi/books", params=params, json=payload)
    retry = await client.post("/v1/shelves/scifi/books", params=params, json=payload)

    assert first.content == retry.content


@pytest.mark.usefixtures("shelf")
async def test_validate_only_does_not_create(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/shelves/scifi/books",
        params={"bookId": "dune", "validateOnly": "true"},
        json={"title": "Dune", "author": "Herbert", "description": ""},
    )

    assert response.status_code == 200
    assert (await client.get("/v1/shelves/scifi/books/dune")).status_code == 404


@pytest.mark.usefixtures("shelf")
async def test_borrow_and_return(client: AsyncClient) -> None:
    _ = await create_book(client, book_id="dune", author="Herbert")

    borrowed = await client.post(
        "/v1/shelves/scifi/books/dune:borrow", json={"borrower": "paul@arrakis.example"}
    )
    again = await client.post("/v1/shelves/scifi/books/dune:borrow", json={"borrower": "x@y"})
    returned = await client.post("/v1/shelves/scifi/books/dune:return")

    assert BookResponse.model_validate_json(borrowed.content).state == "BORROWED"
    assert again.status_code == 400
    assert error_status(again) == "FAILED_PRECONDITION"
    assert BookResponse.model_validate_json(returned.content).borrower is None


@pytest.mark.usefixtures("shelf")
async def test_soft_delete_hides_from_list_until_undelete(client: AsyncClient) -> None:
    _ = await create_book(client, book_id="dune", author="Herbert")

    deleted = await client.delete("/v1/shelves/scifi/books/dune")
    hidden = await client.get("/v1/shelves/scifi/books")
    shown = await client.get("/v1/shelves/scifi/books", params={"showDeleted": "true"})
    _ = await client.post("/v1/shelves/scifi/books/dune:undelete")
    restored = await client.get("/v1/shelves/scifi/books")

    assert BookResponse.model_validate_json(deleted.content).delete_time is not None
    assert ListBooksResponse.model_validate_json(hidden.content).books == []
    assert len(ListBooksResponse.model_validate_json(shown.content).books) == 1
    assert len(ListBooksResponse.model_validate_json(restored.content).books) == 1


@pytest.mark.usefixtures("shelf")
async def test_list_filter_order_and_pages(client: AsyncClient) -> None:
    for book_id, author in [("a", "Le Guin"), ("b", "Herbert"), ("c", "Le Guin"), ("d", "Le Guin")]:
        _ = await create_book(client, book_id=book_id, author=author)
    params = {"filter": 'author = "Le Guin"', "orderBy": "create_time desc"}

    first = ListBooksResponse.model_validate_json(
        (await client.get("/v1/shelves/scifi/books", params=params)).content
    )
    second = ListBooksResponse.model_validate_json(
        (
            await client.get(
                "/v1/shelves/scifi/books", params={**params, "pageToken": first.next_page_token}
            )
        ).content
    )

    # config/test.toml sets default_page_size = 2.
    assert [book.name for book in first.books] == [
        "shelves/scifi/books/d",
        "shelves/scifi/books/c",
    ]
    assert [book.name for book in second.books] == ["shelves/scifi/books/a"]
    assert second.next_page_token == ""


@pytest.mark.usefixtures("shelf")
async def test_page_token_from_other_query_is_rejected(client: AsyncClient) -> None:
    for book_id in ["a", "b", "c"]:
        _ = await create_book(client, book_id=book_id, author="x")
    first = ListBooksResponse.model_validate_json(
        (await client.get("/v1/shelves/scifi/books")).content
    )

    response = await client.get(
        "/v1/shelves/scifi/books",
        params={"pageToken": first.next_page_token, "orderBy": "title"},
    )

    assert response.status_code == 400
    assert error_status(response) == "INVALID_ARGUMENT"


@pytest.mark.usefixtures("shelf")
async def test_read_mask_limits_fields(client: AsyncClient) -> None:
    _ = await create_book(client, book_id="dune", author="Herbert")

    body = json_object(await client.get("/v1/shelves/scifi/books", params={"readMask": "title"}))

    assert body["books"] == [{"name": "shelves/scifi/books/dune", "title": "Dune"}]


@pytest.mark.usefixtures("shelf")
@pytest.mark.parametrize(
    "params",
    [
        {"filter": 'title = "x"'},
        {"orderBy": "isbn"},
        {"readMask": "isbn"},
        {"pageToken": "forged"},
        {"pageSize": "-1"},
    ],
)
async def test_invalid_list_arguments(client: AsyncClient, params: dict[str, str]) -> None:
    response = await client.get("/v1/shelves/scifi/books", params=params)

    assert response.status_code == 400
    assert error_status(response) == "INVALID_ARGUMENT"
