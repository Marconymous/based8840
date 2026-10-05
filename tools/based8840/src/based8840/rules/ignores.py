"""BC009: every `noqa` / `pyright: ignore` comment explains why.

The reason goes after the directive on the same line or in a comment on the line above.
Missing rule codes are caught by ruff PGH and basedpyright reportIgnoreCommentWithoutRule.
"""

import io
import re
import tokenize
from collections.abc import Sequence
from typing import Final

from based8840.findings import Finding, Severity
from based8840.source import SourceModule

DIRECTIVE: Final = re.compile(
    r"#\s*(?:noqa:\s*[A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*|(?:pyright|type):\s*ignore\[[^\]]*\])"
)
REASON_SEPARATORS: Final = " \t-:#\u2013\u2014"  # also en and em dash


def check(module: SourceModule) -> list[Finding]:
    lines: list[str] = module.source.splitlines()
    comments: list[tokenize.TokenInfo] = [
        token
        for token in tokenize.generate_tokens(io.StringIO(module.source).readline)
        if token.type == tokenize.COMMENT
    ]
    return [
        Finding(
            path=module.path,
            line=comment.start[0],
            column=comment.start[1] + 1,
            code="BC009",
            message="Ignore comment without a reason; say why after it or on the line above.",
            severity=Severity.ERROR,
        )
        for comment in comments
        if _lacks_reason(comment, lines)
    ]


def _lacks_reason(comment: tokenize.TokenInfo, lines: Sequence[str]) -> bool:
    directive: re.Match[str] | None = DIRECTIVE.search(comment.string)
    if directive is None:
        return False
    if comment.string[directive.end() :].strip(REASON_SEPARATORS):
        return False
    row: int = comment.start[0]
    line_above: str = lines[row - 2].strip() if row > 1 else ""
    return not line_above.startswith("#")
