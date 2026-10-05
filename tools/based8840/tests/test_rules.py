"""Tests for the AST rules: one bad and one good snippet per case."""

from collections.abc import Callable

import pytest

from based8840.findings import Finding
from based8840.rules import constants, dependencies, enums, ignores, models, rebinding, signatures
from based8840.source import SourceModule
from tests.helpers import make_module

type Check = Callable[[SourceModule], list[Finding]]


def codes(check: Check, source: str) -> list[str]:
    return [finding.code for finding in check(make_module(source, path="src/app/module.py"))]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("def f(point: tuple[int, int]) -> None: ...", ["BC001"]),
        ("def f() -> tuple[int, int]: ...", ["BC001"]),
        ("def f(points: Sequence[tuple[int, int]]) -> None: ...", ["BC001"]),
        ("def f(items: list[int]) -> None: ...", ["BC005"]),
        ("def f(items: dict[str, int] | None) -> None: ...", ["BC005"]),
        ("def f(items: Sequence[int], table: Mapping[str, int]) -> list[int]: ...", []),
        ("def f(items: Set[int]) -> dict[str, int]: ...", []),
        ("def f(self, x): ...", []),
    ],
)
def test_signatures_flags_tuples_and_mutable_parameters(source: str, expected: list[str]) -> None:
    assert codes(signatures.check, source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("MAX_SIZE = 10", ["BC002"]),
        ("MAX_SIZE: int = 10", ["BC002"]),
        ("class A:\n    LIMIT = 3", ["BC002"]),
        ("MAX_SIZE: Final = 10", []),
        ("MAX_SIZE: typing.Final[int] = 10", []),
        ("T = TypeVar('T')", []),
        ("logger = get_logger()", []),
        ("class Color(StrEnum):\n    RED = 'RED'", []),
    ],
)
def test_constants_require_final(source: str, expected: list[str]) -> None:
    assert codes(constants.check, source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("class A(BaseModel):\n    x: int", ["BC003"]),
        ("class A(BaseModel):\n    model_config = ConfigDict(frozen=True)", ["BC003"]),
        ("class A(BaseModel):\n    model_config = ConfigDict(extra='forbid')", ["BC003"]),
        ("class A(BaseModel):\n    model_config = ConfigDict(frozen=True, extra='forbid')", []),
        ("class A(pydantic.BaseModel):\n    model_config = ConfigDict(frozen=False)", ["BC003"]),
        ("class A(ApiModel):\n    x: int", []),
        ("class A(BaseSettings):\n    x: int", []),
        ("class A(SQLModel, table=True):\n    x: int", []),
    ],
)
def test_models_must_be_frozen_and_forbid_extra(source: str, expected: list[str]) -> None:
    assert codes(models.check, source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("ServiceDep = Annotated[Service, Depends(get_service)]", ["BC004"]),
        ("type ServiceDep = Annotated[Service, Depends(get_service)]", ["BC004"]),
        ("ServiceDep: TypeAlias = Annotated[Service, fastapi.Depends(get)]", ["BC004"]),
        ("PageSize = Annotated[int, Field(gt=0)]", []),
    ],
)
def test_dependencies_ban_depends_aliases(source: str, expected: list[str]) -> None:
    assert codes(dependencies.check, source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("class Color(Enum):\n    RED = 1", ["BC006"]),
        ("class Color(StrEnum):\n    RED = 'red'", ["BC006"]),
        ("class Color(StrEnum):\n    RED = auto()", ["BC006"]),
        ("class Color(StrEnum):\n    RED = 'RED'\n    _ignore_ = 'x'", []),
        ("class BookState(StrEnum):\n    AVAILABLE = 'AVAILABLE'", ["BC007"]),
        (
            "class BookState(StrEnum):\n"
            "    STATE_UNSPECIFIED = 'STATE_UNSPECIFIED'\n"
            "    AVAILABLE = 'AVAILABLE'",
            [],
        ),
    ],
)
def test_enums_are_str_enums_named_like_their_values(source: str, expected: list[str]) -> None:
    assert codes(enums.check, source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("def f():\n    x = 1\n    x = 2", ["BC008"]),
        ("def f():\n    x = 1\n    x += 2", ["BC008"]),
        ("def f(x):\n    x = 2", ["BC008"]),
        ("def f(c):\n    x = 1\n    if c:\n        x = 2", ["BC008"]),
        ("def f(c):\n    if c:\n        x = 1\n    else:\n        x = 2\n    x = 3", ["BC008"]),
        ("def f(items):\n    for item in items:\n        row = item\n    item = 1", ["BC008"]),
        ("def f(c):\n    if c:\n        x = 1\n    else:\n        x = 2", []),
        ("def f():\n    try:\n        x = g()\n    except E:\n        x = None", []),
        ("def f(items):\n    for item in items:\n        row = item", []),
        ("def f():\n    x: int\n    x = 1", []),
        ("def f():\n    _ = g()\n    _ = h()", []),
        ("def f():\n    x = 1\n    def g():\n        x = 2", []),
        ("def f(row):\n    row.title = 'a'\n    row.title = 'b'", []),
    ],
)
def test_rebinding_flags_names_bound_twice(source: str, expected: list[str]) -> None:
    assert codes(rebinding.check, source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("x = f()  # pyright: ignore[reportAny]", ["BC009"]),
        ("x = f()  # noqa: ARG001", ["BC009"]),
        ("x = f()  # type: ignore[attr-defined]", ["BC009"]),
        ("x = f()  # noqa: ARG001 - signature fixed by the framework", []),
        ("x = f()  # pyright: ignore[reportAny] - untyped library", []),
        ("# f is untyped.\nx = f()  # pyright: ignore[reportAny]", []),
        ("x = f()  # an ordinary comment", []),
    ],
)
def test_ignore_comments_need_a_reason(source: str, expected: list[str]) -> None:
    assert codes(ignores.check, source) == expected


def test_finding_points_at_the_offending_line() -> None:
    module: SourceModule = make_module("\n\nMAX = 1\n", path="src/app/limits.py")
    findings: list[Finding] = constants.check(module)
    assert [(str(f.path), f.line, f.column) for f in findings] == [("src/app/limits.py", 3, 1)]
