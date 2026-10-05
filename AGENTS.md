# AGENTS.md

Instructions for AI coding agents (Claude Code, Copilot, Codex, Cursor, ...) working in this Python repository. Follow them exactly. When something is unclear or not covered here, see **When to ask** (§2).

Stack: Python ≥3.12 · uv · ruff · basedpyright · pytest · FastAPI (async) · SQLModel · pydantic / pydantic-settings · Atlas.

---

## 1. Commands

Always go through `uv`. Never use `pip`, `pip install`, or bare `python`.

```sh
uv sync                          # install deps from uv.lock
uv add <pkg>                     # add runtime dep (ask first)
uv add --dev <pkg>               # add dev dep (ask first)
uv run ruff format               # format
uv run ruff check --fix          # lint
uv run basedpyright              # type check
uv run pytest -q                 # tests
based8840 verify                 # all of the above (no formatting) + AGENTS.md rule checks, one report
based8840 verify --full          # also the opt-in layer checks (§7)
based8840 format                 # ruff format only
APP_ENV=dev uv run fastapi dev src/app/main.py

atlas migrate diff <name> --env <env>   # generate migration from SQLModel metadata
atlas migrate lint --env <env>          # lint pending migrations
atlas migrate apply --env <env>         # apply migrations
```

Before saying a task is done: format, lint, type check and tests must all pass.

---

## 2. Design principles

Priority order when they conflict: **KISS > YAGNI > DRY > SOLID**.

- Code must be understandable where it is read. A reader must not have to click through 3+ files to find the real implementation.
- A small, readable abstraction beats a long, unreadable inline block. But never add an abstraction for a hypothetical future need.
- Control flow must be obvious from reading the code: no hidden side effects, no magic registration/metaclasses/decorators that change behavior, no deep inheritance.
- Functions stay small: McCabe complexity ≤ 10 and ≤ 40 statements. Enforced by ruff `C901` (`max-complexity = 10`) and `PLR0915` (`max-statements = 40`). Split by responsibility, never by adding ignores.

### When to ask

- **Always ask** before changing a contract: public API shape (paths, fields, status codes), DB schema, dependencies, new config keys, and anything on the never-list (§10).
- **Decide yourself** for internal choices: private helper names, local structure, test layout. Follow the patterns already in the repo; if there are none, pick the simplest option and mention it in your summary.

### Caller orchestrates

If `fn1` produces something that `fn2` consumes, `fn1` returns it to the caller and the caller calls `fn2`. `fn1` never calls `fn2` internally.

```python
# Bad: the chain is hidden inside parse_report
def parse_report(raw: bytes) -> None:
    report: Report = Report.model_validate_json(raw)
    save_report(report)

# Good: the flow is visible at the call site
async def import_report(raw: bytes) -> Report:
    report: Report = parse_report(raw)
    saved: Report = await dao.save(report)
    return saved
```

### One implementation per file, implementations in `impl/`

When abstracting a class (`Protocol` / ABC), the interface lives in `base.py` and each implementation gets its own file. If the folder also contains other files, put all implementations in an `impl/` subfolder.

```
integrations/llm/
  base.py        # LlmClient Protocol
  factory.py     # builds the implementation selected in settings
  impl/
    azure_ai.py  # AzureAiLlmClient
    openai.py    # OpenAiLlmClient
```

### Avoid default parameter values

Parameters are mandatory unless a default is truly necessary or clearly makes more sense than forcing every caller to pass it. Use keyword-only parameters (`*`) when several parameters share a type.

```python
# Bad
def send_mail(to: str, subject: str = "", retries: int = 3, html: bool = False) -> None: ...

# Good
def send_mail(*, to: str, subject: str, body: str, retries: int) -> None: ...
```

Exception: optional API query parameters (`pageSize`, `pageToken`, `filter`, `orderBy`, `showDeleted`, `validateOnly`) may have defaults in route signatures. The default is the AIP "not set" value (`None`, `""`, `False`); a real value such as the default page size is resolved from `Settings`, never a magic number in the signature.

---

## 3. Typing

- Every function signature is fully typed: all parameters and the return type, including `-> None`.
- Annotate variables whose type is not obvious from the line itself, especially results of calls:
  ```python
  user: User = await user_dao.get(user_id)   # yes
  rows: Sequence[BookRow] = result.all()     # yes
  count = 0                                  # obvious literal, no annotation
  ```
- Modern syntax only: `X | None`, `list[int]`, `dict[str, int]`, `type Alias = ...`, PEP 695 generics.
- Parameters take read-only types from `collections.abc` (`Sequence`, `Mapping`, `Set`) so a function cannot mutate its inputs. Return types stay concrete (`list[...]`, `dict[...]`).
  ```python
  def total_price(items: Sequence[LineItem]) -> Decimal: ...   # yes
  def total_price(items: list[LineItem]) -> Decimal: ...       # no
  ```
- Module-level and class-level constants are annotated `Final`: `MAX_PAGE_SIZE: Final = 1000`.
- **`Any` is forbidden** unless there is no way around it. Try first: `object`, a `Protocol`, generics / `TypeVar`, `TypedDict`, a union, or a pydantic model. If `Any` is truly unavoidable, add a comment explaining why.
- `# pyright: ignore[<rule>]` / `# noqa: <code>` only with the exact rule code and a reason comment. Never blanket-ignore.
- Enforced by ruff `ANN` (incl. `ANN401`) and basedpyright (`reportAny`, `reportExplicitAny`).

### Naming

- Classes carry their role as a suffix: `BookDao`, `BookService`, `CreateBookRequest`, `BookResponse`, `LlmClient`. Domain models get the bare noun: `Book`.
- Booleans read as a question: `is_active`, `has_cover`, `can_borrow`.
- Tests: `test_<unit>_<behavior>`, e.g. `test_borrow_twice_fails_precondition`.
- Enums are `StrEnum` whose member name equals its UPPER_SNAKE wire value. State enums start with `STATE_UNSPECIFIED` (§8).
  ```python
  class BookState(StrEnum):
      STATE_UNSPECIFIED = "STATE_UNSPECIFIED"
      AVAILABLE = "AVAILABLE"
  ```
- Absolute imports only (`from app.core.errors import NotFoundError`). Enforced by ruff `ban-relative-imports = "all"`.

---

## 4. Code style

- `pathlib.Path`, never `os.path`.
- f-strings for formatting; `logging` (never `print`) for output in application code.
- No mutable default arguments, no wildcard imports, no module-level mutable state. The one exception is a `contextvars.ContextVar` for request-scoped values such as the request ID: it is per task, not shared.
- Timezone-aware datetimes only: `datetime.now(UTC)`, never naive `datetime.now()`.
- Domain data is a pydantic model, never a bare `dict` passed around as a record.
- Docstrings: one line on every module, and on public classes and functions whose name and types do not already say it all. No `Args:` / `Returns:` sections; the signature is the documentation. Comments explain **why**, never what the next line does.

### Never nest

At most **2 block levels** inside a function body. Use guard clauses, early `return` / `continue`, and extract a function before reaching level 3. Enforced by ruff `PLR1702` (`max-nested-blocks = 2`).

```python
# Bad: 3 levels
def notify(users: Sequence[User]) -> None:
    for user in users:
        if user.active:
            if user.email:
                send_mail(to=user.email)

# Good: guard clauses keep it flat
def notify(users: Sequence[User]) -> None:
    for user in users:
        if not user.active or not user.email:
            continue
        send_mail(to=user.email)
```

### Immutability

- **Bind each name once.** Do not reassign variables; give a transformed value a new name. Prefer comprehensions over loops that accumulate into a mutable list.
  ```python
  # Bad
  name = raw_name.strip()
  name = name.lower()

  # Good
  stripped_name: str = raw_name.strip()
  normalized_name: str = stripped_name.lower()
  ```
- Constants are `Final` (see §3).
- All pydantic models (domain and API) are frozen and reject unknown fields: `model_config = ConfigDict(frozen=True, extra="forbid")`. An unknown field in a request body is a 400 `INVALID_ARGUMENT`. No strict mode: normal type coercion applies. Change models with `model.model_copy(update={...})`.
- Only SQLModel table classes stay mutable, because the ORM requires it. Inside `storage/`, assigning attributes on a row (`row.title = fields.title`) is allowed; local variables are still bound once.
- Do not mutate parameters. Parameters are typed read-only (`Sequence`, `Mapping`, `Set`); build and return a new value instead.

### No tuples in signatures

Never use a tuple as a parameter type or a return type. Use a small frozen pydantic model for multiple values and `Sequence` (parameters) / `list` (returns) for collections.

```python
# Bad
def split_name(full_name: str) -> tuple[str, str]: ...
def distance(a: tuple[float, float], b: tuple[float, float]) -> float: ...

# Good
class NameParts(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    first: str
    last: str

def split_name(full_name: str) -> NameParts: ...
```

Tuples inside a function body are fine: unpacking, `for key, value in mapping.items()`, `select(Book, Shelf)`, `isinstance(x, (A, B))`.

---

## 5. Errors

- Raise specific exceptions; each package defines its own exception hierarchy (e.g. `NotFoundError`, `ConflictError` in `core/errors.py`).
- No bare `except:` or `except Exception:` that swallows errors. Re-raise with `raise ... from e`.
- Services raise domain exceptions. **One** FastAPI exception handler (`api/errors.py`) maps them to AIP error responses (see §8). Routes never build error responses by hand.
- Unexpected exceptions are always logged with their stack trace and returned as 500 `INTERNAL`. What the body contains depends on the `debug_errors` setting (§6):
  - `debug_errors = true` (dev, test): `details` holds a `DebugInfo` with the exception type, message and stack entries.
  - `debug_errors = false` (prod): the message is a generic `"Internal error."` and `details` is empty. Nothing internal reaches the client.

---

## 6. Configuration

```
config/
  base.toml    # shared non-secret values
  dev.toml     # per-environment overrides (add staging.toml, test.toml, ... freely)
  prod.toml
.env           # local secrets only, gitignored
```

- `APP_ENV` is **required** at startup and selects `config/<APP_ENV>.toml`. If it is missing or the file does not exist, the app crashes immediately. There is no default.
- **Non-secret values come only from TOML.** `base.toml` is deep-merged with `<APP_ENV>.toml`, then validated by the `Settings` pydantic model in `core/settings.py`. `Settings` fields have no defaults, so the merged TOML must be complete. Non-secret values cannot be overridden by environment variables.
- **Secrets come only from environment variables** (plus `.env` for local development) through a separate pydantic-settings `Secrets` model with `SecretStr` fields. Secrets are never written to TOML or logged.
- `load_config()` builds both models once at startup and provides `AppConfig(settings=..., secrets=...)` through a FastAPI dependency. No code reads config through implicit module-level globals.
- Behavior that differs per environment is a named setting, never a check on the environment name. Write `if settings.debug_errors:`, not `if app_env != "prod":`. Examples: `debug_errors`, `log_format`.

---

## 7. Architecture

```
src/app/
  main.py                     # app factory: load config, mount routers, register error handler
  api/
    errors.py                 # domain exception -> AIP error response handler
    request_id.py             # X-Request-Id middleware (sets the logging ContextVar)
    pagination.py             # page token encode/decode
    v1/
      router.py               # mounts all v1 routers under /v1
      routers/<resource>.py   # HTTP only: schema -> domain, call service, domain -> schema
  services/<resource>.py      # business logic; no HTTP, no ORM
  storage/
    db/                       # engine, AsyncSession, get_session dependency
    daos/<resource>.py        # DB access; takes and returns domain models only
  models/
    sql/<resource>.py         # SQLModel table=True classes (ORM). Only storage/ (and models/sql) may import these
    domain/<resource>.py      # code-only pydantic models (frozen)
    api/v1/<resource>.py      # API request/response schemas (camelCase, field behavior)
  core/                       # settings loader, logging, errors, generic helpers
  integrations/<name>/        # external systems (Azure AI, Splunk, ...): base.py + impl/
config/                       # TOML per environment
migrations/                   # Atlas versioned migrations + atlas.sum
atlas.hcl
```

### Layer rules

| Layer | May use | Must not |
|---|---|---|
| `api/` routers | services, `models/api`, `models/domain` | contain business logic, touch DB/ORM |
| `services/` | DAOs, integrations, `models/domain` | know about HTTP, schemas, or ORM classes |
| `storage/daos/` | `models/sql`, `models/domain`, session | commit transactions, return ORM objects |
| `integrations/` | external SDKs, `models/domain` | return raw SDK objects |

- Routes are thin: every route delegates to one service call. This keeps files small.
- **ORM → DAO → domain model.** DAOs convert rows with `Model.model_validate(row, from_attributes=True)`. Code that calls a DAO never sees a SQLModel table class. Enforced by ruff `TID251` (banned import of `app.models.sql` outside `storage/`).
- API schemas and domain models are separate classes. The mappers live on the API schema: `BookResponse.from_domain(book)` and `CreateBookRequest.to_domain()`. The router calls them. Domain models never import API schemas.
- Dependency injection uses a FastAPI `Depends` chain. Write `Annotated[..., Depends(...)]` inline in the parameter list. Never create type aliases like `BookServiceDep = Annotated[...]`, because they force the reader to look the alias up.
  ```python
  async def get_book_dao(session: Annotated[AsyncSession, Depends(get_session)]) -> BookDao:
      return BookDao(session)

  async def get_book_service(dao: Annotated[BookDao, Depends(get_book_dao)]) -> BookService:
      return BookService(dao)

  @router.get("/books/{book}")
  async def get_book(
      book: str,
      service: Annotated[BookService, Depends(get_book_service)],
  ) -> BookResponse:
      found: Book = await service.get(book_id=book)
      return BookResponse.from_domain(found)
  ```
- **Transactions are request-scoped.** `get_session` commits when the request succeeds and rolls back on exception. Services and DAOs never call `commit()`; DAOs may `flush()` when they need generated values.
- Fully async: `async def` everywhere in the request path, `AsyncSession`, async drivers. No blocking I/O in async code.
  - Run concurrent work in an `asyncio.TaskGroup`, not `asyncio.gather`.
  - Wrap a sync-only SDK call in `await asyncio.to_thread(...)`.

### Resource IDs and database

- The client may choose the ID (`bookId` on Create). It must match `^[a-z][a-z0-9-]{0,62}$`, otherwise the request is `INVALID_ARGUMENT`. Without one, the server generates `<prefix>-<12 hex chars>` (`core/ids.py`).
- The string ID is the table's primary key. The full resource `name` is derived from the IDs and never stored.
- The DB engine is chosen per project and named in its README. Keep code engine-neutral: no raw SQL with engine-specific syntax outside `migrations/`.

### Integrations

- HTTP calls use one shared `httpx.AsyncClient` per integration, created at startup and closed in the lifespan.
- Every external call has a timeout read from `Settings`. No call without one.
- Retries are explicit, bounded (attempt count from `Settings`), use backoff, and only wrap idempotent calls.
- SDK errors are translated to the integration's own exceptions at the integration boundary (§5).

### Auth

- Authentication: OAuth2 bearer JWT, validated in one FastAPI dependency that returns a domain `Principal`. Routes receive it via `Annotated[Principal, Depends(get_principal)]` and pass it to the service.
- Authorization lives in services, not routes.
- A missing or invalid token is 401 `UNAUTHENTICATED`. A resource the caller may not see is 404 `NOT_FOUND`, so its existence is not leaked. 403 `PERMISSION_DENIED` is only for resources the caller can see but not change.
- JWT validation needs a library. Ask before adding it (§10).

### Logging

- stdlib `logging` only, one logger per module: `logger: Final = logging.getLogger(__name__)`.
- Format comes from `Settings.log_format`: `"json"` (one JSON object per line, for prod) or `"text"` (dev).
- Every log line carries a `request_id`. A middleware takes it from the `X-Request-Id` header (or generates one), stores it in a `ContextVar`, and echoes it in the response header.
- Levels: `DEBUG` diagnostics; `INFO` state changes (created, deleted, job run); `WARNING` recoverable problems (retry, fallback); `ERROR` / `logger.exception` failed requests and jobs.
- Never log secrets, tokens, or personal data (names, emails, request bodies). Log IDs instead.

### Migrations (Atlas)

- `atlas.hcl` loads the desired schema from `SQLModel.metadata` through `atlas-provider-sqlalchemy` (`data "external_schema"`).
- Change a `models/sql` class, then run `atlas migrate diff <name> --env <env>`, review the generated SQL, and run `atlas migrate lint`.
- Never edit an applied migration or `atlas.sum` by hand. Commit both.

---

## 8. API standards (Google AIP, adapted to FastAPI/JSON)

Reference: https://google.aip.dev. Only the AIPs listed here apply.

### Scope: required vs opt-in
- **Required on every resource:** `name`, the standard methods it supports, AIP-193 errors, pagination on List, `updateMask` on Update.
- **Opt-in per resource:** `etag`, `requestId`, soft delete, `validateOnly`, long-running operations, `readMask`. Add one only when the resource needs it, and state the reason in the resource schema's docstring. When added, follow the rules below exactly.

### Resources (AIP-121, 122, 123, 124, 140, 190)
- Resource-oriented: model the API as resources and collections, not RPC verbs.
- Resource names are paths: `publishers/{publisher}/books/{book}`. Every resource has a `name` field holding its full resource name.
- Collection IDs are plural camelCase nouns; field names are snake_case in Python.

### JSON casing
- camelCase on the wire, snake_case in Python. All API schemas inherit from one base:
  ```python
  class ApiModel(BaseModel):
      model_config = ConfigDict(
          alias_generator=to_camel, populate_by_name=True, frozen=True, extra="forbid"
      )
  ```

### Standard methods (AIP-130 to 136)
| Method | HTTP | Notes |
|---|---|---|
| Get | `GET /v1/books/{book}` | |
| List | `GET /v1/books` | pagination, filter, orderBy |
| Create | `POST /v1/books` | body = resource; optional `bookId` query param |
| Update | `PATCH /v1/books/{book}` | `updateMask` required for partial updates |
| Delete | `DELETE /v1/books/{book}` | returns empty body (or resource if soft delete) |
| Custom | `POST /v1/books/{book}:archive` | verb after colon, camelCase |

### Errors (AIP-193, 143)
Every error uses one body shape:
```json
{"error": {"code": 404, "message": "Book 'books/42' not found.", "status": "NOT_FOUND", "details": []}}
```
Use canonical status codes: `INVALID_ARGUMENT` (400, including validation errors), `UNAUTHENTICATED` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404), `ALREADY_EXISTS` / `ABORTED` (409), `FAILED_PRECONDITION` (400), `RESOURCE_EXHAUSTED` (429), `INTERNAL` (500), `UNAVAILABLE` (503).

### Fields (AIP-142, 148, 203, 216)
- Timestamps: `*_time` suffix, RFC 3339 UTC. Durations: `*_duration`.
- Standard fields where applicable: `name`, `display_name`, `create_time`, `update_time`, `delete_time`, `etag`, `state`.
- Field behavior: OUTPUT_ONLY fields (`name`, `*_time`, `etag`, `state`) are absent from create/update request schemas. REQUIRED fields are documented in the schema docstring / `Field(description=...)`.
- States are an enum whose zero value is `STATE_UNSPECIFIED`.

### Pagination and ordering (AIP-158, 132)
- Request: `pageSize`, `pageToken`. Response: `nextPageToken` (empty string when there are no more pages).
- Page tokens are opaque (encoded, never raw offsets the client can edit). Document the default and maximum `pageSize`.
- `orderBy`: comma-separated fields, optional ` desc`, e.g. `"create_time desc, title"`.

### Filtering and field masks (AIP-160, 161, 157)
- `filter` string on List with a documented subset of the AIP-160 grammar; reject unsupported filters with `INVALID_ARGUMENT`.
- `updateMask` on PATCH: only listed fields change. `*` means full replacement.
- `readMask` for partial responses where payloads are large.

### Concurrency and idempotency (AIP-154, 155)
- Resources expose an `etag`. Update/Delete accept `etag`; a mismatch returns `ABORTED`.
- Create accepts `requestId` (UUID). Repeating a request with the same `requestId` returns the original result instead of creating a duplicate.

### Lifecycle (AIP-163, 164, 151, 152)
- Soft delete: Delete sets `delete_time`; provide `:undelete`; List hides deleted resources unless `showDeleted=true`.
- `validateOnly=true` on mutations validates without persisting.
- Long-running work returns an `operations/{operation}` resource that the client polls.
- Recurring/configurable work is modelled as a Job resource with `:run`.

### Versioning (AIP-185, 180, 181)
- Major version in the path: `/v1`, `/v2`. API code lives in `api/v1/`, schemas in `models/api/v1/`.
- Within a version, only backwards-compatible changes: add optional fields/methods, never remove or rename.
- Document each surface's stability level (alpha / beta / stable).

---

## 9. Testing

- pytest with `pytest-asyncio` (auto mode) and `httpx.AsyncClient` against the app; tests run with `APP_ENV=test` and `config/test.toml`.
- Services: unit-tested with a fake DAO (a class implementing the same methods), no database.
- DAOs: tested against a real test database built from the Atlas migrations (so schema drift fails tests). On SQLite: a fresh database file under `tmp_path` per test. On other engines: that engine via testcontainers, never SQLite as a stand-in.
- Routers: assert AIP shapes (status codes, error body, camelCase fields, pagination tokens).
- Plain `assert`, fixtures over setup classes, `@pytest.mark.parametrize` for variants, `tmp_path` for files. No network in unit tests.
- New behavior needs a test. A bug fix starts with a failing regression test.

---

## 10. Agent workflow

- Run format, lint, type check and tests before claiming done. Report failures honestly.
- Keep diffs minimal. No drive-by refactors, renames or reformatting of unrelated code.
- Ask before adding a dependency, and justify it; prefer the standard library.
- Never hand-edit `uv.lock`, `atlas.sum` or applied migrations.
- Never weaken lint/type config or add ignores to make checks pass.
- When requirements are ambiguous, ask instead of guessing (see **When to ask**, §2).

### Git

- Conventional Commits: `type(scope): subject`, imperative, lowercase, no trailing period. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `build`, `ci`.
- Commit only when asked. One logical change per commit.
- Never commit on `main`. Never push. Never force-push.

### Never without explicit permission

- `atlas migrate apply` against anything but a local or test database.
- Editing `config/prod.toml` or `.env`, or printing secret values.
- Destructive commands: `git reset --hard`, `git clean`, `rm -rf`, deleting files the task did not create.
- Network calls (HTTP requests, external APIs, cloud CLIs). `uv sync` / `uv add` after approval are fine.
