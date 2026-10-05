"""Prints the SQLite DDL of all SQLModel tables. atlas.hcl reads it as the desired schema.

Run: uv run python -m app.storage.db.schema
"""

from atlas_provider_sqlalchemy.ddl import print_ddl

from app.models.sql.book import BookRow
from app.models.sql.job import JobRow
from app.models.sql.operation import OperationRow
from app.models.sql.shelf import ShelfRow

if __name__ == "__main__":
    print_ddl("sqlite", [ShelfRow, BookRow, OperationRow, JobRow])
