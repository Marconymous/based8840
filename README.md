# based8840

Opinionated agent configuration for Python / FastAPI projects. One instruction file, read by every harness.

| File | Read by |
|---|---|
| `AGENTS.md` | Source of truth. Codex, Cursor, Copilot, and other AGENTS.md-aware agents |
| `CLAUDE.md` | Claude Code (imports `AGENTS.md` via `@AGENTS.md`, plus Claude-only notes) |
| `.github/copilot-instructions.md` | GitHub Copilot (symlink to `AGENTS.md`) |
| `.claude/settings.json` + `.claude/hooks/` | Claude Code hooks: ruff after each `.py` edit, basedpyright before a turn ends |
| `pyproject.toml` | Reference ruff / basedpyright / pytest config the rules rely on |

Edit only `AGENTS.md`; the other instruction files follow it.

## Example

[`examples/library`](examples/library) is a runnable FastAPI + SQLite app that applies every rule in `AGENTS.md`, with a table mapping each rule to the file that shows it. No network access needed.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- `jq` (used by the hooks)
- [Atlas](https://atlasgo.io/) for migrations

Dev dependencies in the target project: `uv add --dev ruff basedpyright pytest pytest-asyncio httpx`.

## Adopt in a project

```sh
cp -a AGENTS.md CLAUDE.md .github .claude /path/to/project/
```

`cp -a` keeps the symlink. Then merge the `[tool.*]` sections of `pyproject.toml` into the project's `pyproject.toml`.

The banned-import rule assumes the package is `src/app`. Rename `app` in `[tool.ruff.lint.flake8-tidy-imports.banned-api]` and the per-file-ignores if your package is named differently.

## Atlas

Example `atlas.hcl` loading the schema from SQLModel metadata via [`atlas-provider-sqlalchemy`](https://github.com/ariga/atlas-provider-sqlalchemy):

```hcl
data "external_schema" "sqlmodel" {
  program = [
    "uv", "run", "atlas-provider-sqlalchemy",
    "--path", "./src/app/models/sql",
    "--dialect", "postgresql",
  ]
}

env "dev" {
  src = data.external_schema.sqlmodel.url
  dev = "docker://postgres/16/dev?search_path=public"
  migration {
    dir = "file://migrations"
  }
  format {
    migrate {
      diff = "{{ sql . \"  \" }}"
    }
  }
}
```

## Hooks

- `py-postedit.sh` (PostToolUse on `Edit|Write|MultiEdit`): runs `ruff check --fix` and `ruff format` on the edited `.py` file, inside the nearest directory whose `pyproject.toml` has a `[project]` table. Remaining violations are sent back to Claude (exit 2).
- `py-stop.sh` (Stop): runs `basedpyright` in every project (`pyproject.toml` with `[project]`, up to 3 levels deep, e.g. the repo root or `examples/*`). Errors block the turn once; `stop_hook_active` prevents an endless loop.

Both exit silently when `uv` is missing or the file is not Python. Tests are not run in hooks (too slow); `AGENTS.md` requires the agent to run them.

## License

[MIT](LICENSE)
