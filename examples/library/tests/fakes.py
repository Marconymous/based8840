"""In-memory fakes. They satisfy the Protocols in app.storage.daos.base and
app.integrations.notifier.base structurally, so services can be tested without a database."""

from datetime import datetime

from app.models.domain.book import Book, BookQuery
from app.models.domain.job import Job
from app.models.domain.notification import Notification
from app.models.domain.page import Page, PageRequest
from app.models.domain.shelf import Shelf


class FakeShelfDao:
    def __init__(self) -> None:
        self.shelves: dict[str, Shelf] = {}

    async def find(self, shelf_id: str) -> Shelf | None:
        return self.shelves.get(shelf_id)

    async def list_page(self, page: PageRequest) -> Page[Shelf]:
        shelves: list[Shelf] = list(self.shelves.values())
        end: int = page.offset + page.limit
        return Page(items=shelves[page.offset : end], has_more=len(shelves) > end)

    async def insert(self, shelf: Shelf) -> Shelf:
        self.shelves[shelf.shelf_id] = shelf
        return shelf

    async def update(self, shelf: Shelf) -> Shelf:
        self.shelves[shelf.shelf_id] = shelf
        return shelf

    async def delete(self, shelf_id: str) -> None:
        del self.shelves[shelf_id]


class FakeBookDao:
    def __init__(self) -> None:
        self.books: dict[str, Book] = {}

    async def find(self, *, shelf_id: str, book_id: str) -> Book | None:
        return self.books.get(f"{shelf_id}/{book_id}")

    async def find_by_request_id(self, request_id: str) -> Book | None:
        return next((book for book in self.books.values() if book.request_id == request_id), None)

    async def list_page(self, query: BookQuery) -> Page[Book]:
        books: list[Book] = [
            book for book in self.books.values() if book.shelf_id == query.shelf_id
        ]
        end: int = query.page.offset + query.page.limit
        return Page(items=books[query.page.offset : end], has_more=len(books) > end)

    async def list_in_shelf(self, shelf_id: str) -> list[Book]:
        return [book for book in self.books.values() if book.shelf_id == shelf_id]

    async def list_due_before(self, due_before: datetime) -> list[Book]:
        return [
            book
            for book in self.books.values()
            if book.due_time is not None and book.due_time < due_before
        ]

    async def count_in_shelf(self, shelf_id: str) -> int:
        return len(await self.list_in_shelf(shelf_id))

    async def insert(self, book: Book) -> Book:
        self.books[f"{book.shelf_id}/{book.book_id}"] = book
        return book

    async def update(self, book: Book) -> Book:
        self.books[f"{book.shelf_id}/{book.book_id}"] = book
        return book


class FakeJobDao:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}

    async def find(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    async def list_page(self, page: PageRequest) -> Page[Job]:
        jobs: list[Job] = list(self.jobs.values())
        end: int = page.offset + page.limit
        return Page(items=jobs[page.offset : end], has_more=len(jobs) > end)

    async def insert(self, job: Job) -> Job:
        self.jobs[job.job_id] = job
        return job

    async def update(self, job: Job) -> Job:
        self.jobs[job.job_id] = job
        return job


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    async def send(self, notification: Notification) -> None:
        self.sent.append(notification)
