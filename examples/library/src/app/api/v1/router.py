"""Mounts every v1 resource router under /v1."""

from typing import Final

from fastapi import APIRouter

from app.api.v1.routers import books, jobs, operations, shelves

router = APIRouter(prefix="/v1")
router.include_router(shelves.router)
router.include_router(books.router)
router.include_router(operations.router)
router.include_router(jobs.router)

# Stability level of each surface (AIP-181), shown in the OpenAPI docs at /docs.
OPENAPI_TAGS: Final = [
    {"name": "shelves", "description": "Stability: **stable**."},
    {"name": "books", "description": "Stability: **stable**."},
    {"name": "operations", "description": "Stability: **beta**. Long-running exports."},
    {"name": "jobs", "description": "Stability: **alpha**. Recurring work, run via `:run`."},
]
