@AGENTS.md

## Claude Code specifics

- A PostToolUse hook runs `ruff format` and `ruff check --fix` on every `.py` file you edit. Fix any violations it reports; do not fight the formatter.
- A Stop hook runs `basedpyright`. Your turn is blocked until type errors are fixed.
