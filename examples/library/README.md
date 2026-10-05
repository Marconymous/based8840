# Library example

A small library API (shelves, books, borrowing, exports, reminder jobs) that follows every
rule in [`AGENTS.md`](../../AGENTS.md). It runs fully offline: SQLite via `aiosqlite`, a
notifier that writes to the log or a local file, and exports to a local folder.

Use it as a reference: when a rule in `AGENTS.md` is unclear, the table below shows where it
is applied.

## Quickstart

Needs [uv](https://docs.astral.sh/uv/) and [Atlas](https://atlasgo.io/) (`brew install uv ariga/tap/atlas`).

```sh
cd examples/library
uv sync
cp .env.example .env                       # secrets: PAGE_TOKEN_SECRET
atlas migrate apply --env dev              # creates library.db from migrations/
APP_ENV=dev uv run fastapi dev src/app/main.py
```

Open http://127.0.0.1:8000/docs for the OpenAPI UI.

### Demo data

`seed/demo.sql` holds 4 shelves, 21 books (6 borrowed, `classics/middlemarch` soft-deleted)
and 2 overdue-reminder jobs. It is data only; load it after the migrations:

```sh
rm -f library.db
atlas migrate apply --env dev
sqlite3 library.db < seed/demo.sql
```

Loans were made on 2026-10-05 with a 14-day loan, so from 2026-10-19 on
`POST /v1/jobs/overdue-reminders:run` finds overdue books.

To regenerate it after changing the data through the API:

```sh
{ echo "BEGIN TRANSACTION;"
  for t in shelves books jobs; do sqlite3 library.db ".mode insert $t" "SELECT * FROM $t ORDER BY create_time"; done
  echo "COMMIT;"; } > seed/demo.sql
```

Checks (all must pass before a change is done):

```sh
uv run ruff format && uv run ruff check --fix && uv run basedpyright && uv run pytest -q
```

## Walkthrough

```sh
B=http://127.0.0.1:8000/v1
J='content-type: application/json'

# Create (client-chosen ID) and read
curl -s -XPOST "$B/shelves?shelfId=fantasy" -H "$J" -d '{"displayName":"Fantasy","genre":"fantasy"}'
curl -s -XPOST "$B/shelves/fantasy/books?bookId=earthsea" -H "$J" \
  -d '{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin","description":""}'
curl -s "$B/shelves/fantasy/books/earthsea"

# Idempotent create: same requestId twice -> one book
curl -s -XPOST "$B/shelves/fantasy/books?requestId=6f1c2a0e-9d7b-4a43-8a52-1f0f3b8e2c11" -H "$J" \
  -d '{"title":"Tehanu","author":"Ursula K. Le Guin","description":""}'

# Custom methods; borrowing twice -> 400 FAILED_PRECONDITION
curl -s -XPOST "$B/shelves/fantasy/books/earthsea:borrow" -H "$J" -d '{"borrower":"ged@roke.example"}'
curl -s -XPOST "$B/shelves/fantasy/books/earthsea:borrow" -H "$J" -d '{"borrower":"someone@else"}'

# List with filter, ordering, field mask and pagination
curl -s -G "$B/shelves/fantasy/books" \
  --data-urlencode 'filter=state = "BORROWED"' \
  --data-urlencode 'orderBy=create_time desc' \
  --data-urlencode 'readMask=title,state' \
  --data-urlencode 'pageSize=1'

# Partial update with updateMask; a stale etag -> 409 ABORTED
curl -s -XPATCH "$B/shelves/fantasy?updateMask=genre" -H "$J" -d '{"genre":"high fantasy"}'
curl -s -XPATCH "$B/shelves/fantasy?etag=stale" -H "$J" -d '{"genre":"x"}'

# Soft delete, list with showDeleted, undelete
curl -s -XDELETE "$B/shelves/fantasy/books/earthsea"
curl -s "$B/shelves/fantasy/books?showDeleted=true"
curl -s -XPOST "$B/shelves/fantasy/books/earthsea:undelete"

# Long-running export: returns operations/{id}; poll it
curl -s -XPOST "$B/shelves/fantasy:exportBooks"
curl -s "$B/operations/<id from above>"

# Recurring work modelled as a Job resource
curl -s -XPOST "$B/jobs?jobId=overdue" -H "$J" \
  -d '{"displayName":"Overdue reminders","kind":"OVERDUE_REMINDER","graceDays":0}'
curl -s -XPOST "$B/jobs/overdue:run"       # dev writes reminders to notifications.jsonl
```

## Where each rule lives

| AGENTS.md | Rule | Example |
|---|---|---|
| §1 | Everything through `uv` | `pyproject.toml`, `uv.lock` |
| §2 | Caller orchestrates | `services/jobs.py` `JobService.run` (DAO → `overdue_reminder` → notifier); `api/background.py` `run_export` |
| §2 | `base.py` + one implementation per file in `impl/` | `integrations/notifier/`, `storage/daos/` |
| §2 | No defaults, keyword-only params | `services/*.py` constructors and methods; route signatures with `*` in `api/v1/routers/books.py` |
| §2 | Complexity ≤ 10, ≤ 40 statements (ruff `C901`, `PLR0915`) | `pyproject.toml` `[tool.ruff.lint.mccabe]`, `[tool.ruff.lint.pylint]` |
| §3 | Annotated call results, `Final`, read-only params | everywhere; e.g. `core/patch.py` (`Set`), `api/errors.py` (`Final` mappings) |
| §3 | PEP 695 generics | `models/domain/page.py` `Page[T]`, `storage/daos/base.py` `to_page[T]` |
| §3 | `Any` only with a reason | `api/dependencies.py` `get_resources` (Starlette types `app.state` as `Any`) |
| §3 | Ignores carry the exact rule + reason | `models/sql/*.py`, `core/settings.py`, `models/sql/types.py` |
| §4 | `pathlib`, `logging`, aware datetimes | `services/operations.py`, `integrations/notifier/impl/log.py`, `core/clock.py`, `models/sql/types.py` (rejects naive datetimes) |
| §4 | Max 2 nesting levels | `api/ordering.py` (`match` instead of nested `if`), `api/background.py` |
| §4 | Bind once, frozen models, `model_copy` | `services/books.py` (`borrow`, `delete`, ...) |
| §4 | No tuples in signatures | `api/pagination.py` `PageCursor`, `api/filtering.py` `FilterTerm`, `models/domain/operation.py` `ExportResult` |
| §5 | Domain exceptions, one handler | `core/errors.py` → `api/errors.py` |
| §5 | `debug_errors`: `DebugInfo` in non-prod 500s, generic in prod | `api/errors.py` `handle_unexpected_error`, `config/*.toml`, `tests/api/test_errors.py` |
| §6 | TOML per env, no defaults, crash without `APP_ENV` | `config/*.toml`, `core/settings.py`, `main.py` |
| §6 | Secrets only from env / `.env` | `core/settings.py` `Secrets`, `.env.example` |
| §6 | Per-environment behavior is a named setting | `Settings.debug_errors`, `Settings.log_format` |
| §7 | Layers and thin routes | `api/v1/routers/` → `services/` → `storage/daos/` |
| §7 | ORM private to storage (ruff `TID251`) | `models/sql/` imported only by `storage/` |
| §7 | DAO converts with `model_validate(row, from_attributes=True)` | `storage/daos/impl/*.py` |
| §7 | Inline `Annotated[..., Depends(...)]`, no aliases | `api/dependencies.py`, every router |
| §7 | Request-scoped transaction, DAOs only `flush()` | `storage/db/session.py` `session_scope`, `api/dependencies.py` `get_session` |
| §7 | Atlas migrations from SQLModel metadata | `atlas.hcl`, `storage/db/schema.py`, `migrations/` |
| §7 | Logging: JSON/text, `request_id` on every line | `core/log_setup.py`, `core/request_context.py`, `api/request_id.py` |
| §8 | Resource names, camelCase JSON | `core/ids.py`, `models/api/v1/base.py` `ApiModel` |
| §4 / §8 | `extra="forbid"`: unknown body fields are 400 | `models/api/v1/base.py` `ApiModel`, `tests/api/test_errors.py` |
| §8 | Standard + custom methods | `api/v1/routers/books.py` (`:borrow`, `:return`, `:undelete`) |
| §8 | AIP-193 errors | `api/errors.py`, `models/api/v1/error.py` |
| §8 | Field behavior (OUTPUT_ONLY / REQUIRED) | `models/api/v1/*.py` `Field(description=...)` |
| §8 | `STATE_UNSPECIFIED` zero value | `models/domain/book.py` `BookState` |
| §8 | Opaque page tokens, `pageSize` default/max | `api/pagination.py`, `config/base.toml` |
| §8 | `filter`, `orderBy` | `api/filtering.py`, `api/ordering.py` |
| §8 | `updateMask`, `readMask` | `api/field_mask.py`, `core/patch.py`, `list_books` |
| §8 | `etag` → `ABORTED`, `requestId` idempotency | `core/ids.py` `check_etag`, `services/books.py` `create` |
| §8 | Soft delete, `showDeleted`, `validateOnly` | `services/books.py`, `storage/daos/impl/books.py` |
| §8 | Long-running operations | `POST /v1/shelves/{shelf}:exportBooks`, `api/v1/routers/operations.py` |
| §8 | Job resource with `:run` | `api/v1/routers/jobs.py`, `services/jobs.py` |
| §8 | Versioning and stability levels | `/v1` prefix and `OPENAPI_TAGS` in `api/v1/router.py` |
| §9 | Services with fakes, no database | `tests/services/`, `tests/fakes.py` |
| §9 | DAOs against a real database | `tests/daos/` (SQLite in `tmp_path`, built from `migrations/`) |
| §9 | Routers assert AIP shapes | `tests/api/` |
| §9 | `parametrize`, `tmp_path`, plain `assert` | `tests/test_list_query.py`, `tests/conftest.py` |

## Notes

- Tests build their database by running the SQL files in `migrations/`, so a model change
  without a new migration fails the DAO and API tests.
- `atlas migrate lint` needs an Atlas Pro login (since Atlas v0.38). Without one, review the
  generated SQL by hand.
- `GET` on a soft-deleted book still returns it (with `deleteTime`); `List` hides it unless
  `showDeleted=true` (AIP-164).
- Export runs as a FastAPI background task after the response. It opens its own transaction
  because the request's session is already committed by then.
