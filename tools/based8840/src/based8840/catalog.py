"""Rules based8840 reports itself: AGENTS.md section, rationale, a bad and a good example."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Rule:
    code: str
    title: str
    section: str
    step: str
    rationale: str
    bad: str
    good: str


RULE_LIST: Final = [
    Rule(
        code="BC001",
        title="No tuples in parameter or return types",
        section="§4 No tuples in signatures",
        step="rules",
        rationale=(
            "A tuple says nothing about what each position means, and callers unpack it by "
            "position. A small frozen model names every value."
        ),
        bad="def split_name(full_name: str) -> tuple[str, str]: ...",
        good=(
            "class NameParts(BaseModel):\n"
            '    model_config = ConfigDict(frozen=True, extra="forbid")\n'
            "    first: str\n"
            "    last: str\n"
            "\n"
            "def split_name(full_name: str) -> NameParts: ..."
        ),
    ),
    Rule(
        code="BC002",
        title="Module- and class-level constants are Final",
        section="§3 Final constants",
        step="rules",
        rationale=(
            "`Final` lets the type checker reject a reassignment, so a constant really stays "
            "constant and readers know it is never changed elsewhere."
        ),
        bad="MAX_PAGE_SIZE = 1000",
        good="MAX_PAGE_SIZE: Final = 1000",
    ),
    Rule(
        code="BC003",
        title='Direct BaseModel subclasses set ConfigDict(frozen=True, extra="forbid")',
        section="§4 Immutability",
        step="rules",
        rationale=(
            "Frozen models cannot change behind the caller's back, and rejecting unknown fields "
            "turns a typo in a request body into a 400 instead of silently dropped data."
        ),
        bad="class Book(BaseModel):\n    title: str",
        good=(
            "class Book(BaseModel):\n"
            '    model_config = ConfigDict(frozen=True, extra="forbid")\n'
            "    title: str"
        ),
    ),
    Rule(
        code="BC004",
        title="No aliases for Annotated[..., Depends(...)]",
        section="§7 Dependency injection",
        step="rules",
        rationale=(
            "An alias hides which dependency a route gets; the reader has to look it up. "
            "Written inline, the whole Depends chain is visible in the signature."
        ),
        bad=(
            "BookServiceDep = Annotated[BookService, Depends(get_book_service)]\n"
            "\n"
            "async def get_book(book: str, service: BookServiceDep) -> BookResponse: ..."
        ),
        good=(
            "async def get_book(\n"
            "    book: str,\n"
            "    service: Annotated[BookService, Depends(get_book_service)],\n"
            ") -> BookResponse: ..."
        ),
    ),
    Rule(
        code="BC005",
        title="Parameters take Sequence / Mapping / Set, not list / dict / set",
        section="§3 Read-only parameters",
        step="rules",
        rationale=(
            "Read-only parameter types make it a type error for a function to mutate its "
            "inputs, and accept more argument types (tuples, frozensets, other mappings)."
        ),
        bad="def total_price(items: list[LineItem]) -> Decimal: ...",
        good="def total_price(items: Sequence[LineItem]) -> Decimal: ...",
    ),
    Rule(
        code="BC006",
        title="Enums are StrEnum with value equal to member name",
        section="§3 Naming",
        step="rules",
        rationale=(
            "The member name is the wire value, so JSON, logs, the database and the code all "
            "spell a value the same way."
        ),
        bad='class BookState(Enum):\n    AVAILABLE = "available"',
        good='class BookState(StrEnum):\n    AVAILABLE = "AVAILABLE"',
    ),
    Rule(
        code="BC007",
        title="*State enums start with STATE_UNSPECIFIED",
        section="§8 States",
        step="rules",
        rationale=(
            "AIP-216: the zero value of a state means 'not set', so a missing state is never "
            "mistaken for a real one."
        ),
        bad='class BookState(StrEnum):\n    AVAILABLE = "AVAILABLE"',
        good=(
            "class BookState(StrEnum):\n"
            '    STATE_UNSPECIFIED = "STATE_UNSPECIFIED"\n'
            '    AVAILABLE = "AVAILABLE"'
        ),
    ),
    Rule(
        code="BC008",
        title="A name is bound once per function (sibling branches may each bind it)",
        section="§4 Bind each name once",
        step="rules",
        rationale=(
            "When every name has one value, a reader can trust a name wherever they see it, "
            "and each transformation step gets a name that says what it produced."
        ),
        bad="name = raw_name.strip()\nname = name.lower()",
        good=(
            "stripped_name: str = raw_name.strip()\nnormalized_name: str = stripped_name.lower()"
        ),
    ),
    Rule(
        code="BC009",
        title="noqa / pyright: ignore comments give a reason",
        section="§3 Ignore comments",
        step="rules",
        rationale=(
            "An ignore without a reason cannot be reviewed: nobody knows whether it is still "
            "needed or was added to make a check pass."
        ),
        bad="return json.loads(text)  # pyright: ignore[reportAny]",
        good=(
            "# json.loads is typed as returning Any; the caller narrows the result.\n"
            "return json.loads(text)  # pyright: ignore[reportAny]"
        ),
    ),
    Rule(
        code="BL001",
        title="Layer import rules (routers, services, DAOs, integrations, domain models)",
        section="§7 Layer rules",
        step="layers",
        rationale=(
            "Each layer has one job. Routers do HTTP, services do business logic, DAOs do "
            "storage. Imports across those lines leak HTTP or ORM details into the wrong place."
        ),
        bad="# src/app/services/books.py\nfrom app.models.api.v1.books import BookResponse",
        good="# src/app/services/books.py\nfrom app.models.domain.books import Book",
    ),
    Rule(
        code="BL002",
        title="Services, DAOs and routers never commit()",
        section="§7 Layer rules",
        step="layers",
        rationale=(
            "Transactions are request-scoped: get_session commits on success and rolls back on "
            "error. A commit inside a service or DAO breaks that all-or-nothing guarantee."
        ),
        bad="await self._session.commit()",
        good="await self._session.flush()  # only when generated values are needed",
    ),
    Rule(
        code="BD001",
        title="Reference ruff rule not selected",
        section="§10 Never weaken lint config",
        step="config",
        rationale=(
            "Every selected rule family enforces part of AGENTS.md. Dropping one from "
            "`select` silently turns its rules off."
        ),
        bad='select = ["E", "F"]',
        good='select = ["E", "W", "F", "I", "N", "UP", "B", ...]  # as in the reference',
    ),
    Rule(
        code="BD002",
        title="New ignore or exclude",
        section="§10 Never weaken lint config",
        step="config",
        rationale=(
            "An ignore or exclude that the reference does not have switches a check off for "
            "the whole project or a set of files. Fix the code instead."
        ),
        bad='ignore = ["PLR0913", "ANN401"]',
        good='ignore = ["PLR0913"]',
    ),
    Rule(
        code="BD003",
        title="Complexity, nesting or statement limit raised",
        section="§10 Never weaken lint config",
        step="config",
        rationale=(
            "The limits keep functions small and flat (§2, §4). A missing limit falls back to "
            "ruff's looser default."
        ),
        bad="[tool.ruff.lint.mccabe]\nmax-complexity = 20",
        good="[tool.ruff.lint.mccabe]\nmax-complexity = 10",
    ),
    Rule(
        code="BD004",
        title="Ruff setting weakened",
        section="§10 Never weaken lint config",
        step="config",
        rationale=(
            "preview is needed for PLR1702 (never nest), ban-relative-imports keeps imports "
            "absolute, and banned-api keeps ORM classes in storage/ and gather out of the code."
        ),
        bad='[tool.ruff.lint.flake8-tidy-imports]\nban-relative-imports = "parents"',
        good='[tool.ruff.lint.flake8-tidy-imports]\nban-relative-imports = "all"',
    ),
    Rule(
        code="BD005",
        title="basedpyright setting weakened",
        section="§10 Never weaken lint config",
        step="config",
        rationale=(
            "The type checker enforces §3: a lower typeCheckingMode or Any reports below "
            "error let untyped code through."
        ),
        bad='[tool.basedpyright]\ntypeCheckingMode = "basic"\nreportAny = "warning"',
        good='[tool.basedpyright]\ntypeCheckingMode = "standard"\nreportAny = "error"',
    ),
    Rule(
        code="BA001",
        title="Atlas migration directory is not valid",
        section="§7 Migrations",
        step="atlas",
        rationale=(
            "atlas.sum must match the migration files, and every migration must replay on the "
            "dev database. A mismatch means a migration was edited or added by hand."
        ),
        bad="vim migrations/20260101000000_init.sql  # edit an applied migration",
        good="atlas migrate diff add_isbn --env dev  # new migration, atlas.sum updated",
    ),
]

RULES: Final = {rule.code: rule for rule in RULE_LIST}
