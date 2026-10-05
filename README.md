# based8840

Opinionated agent configuration for Python / FastAPI projects. One instruction file, read by every harness.

| File | Read by |
|---|---|
| `AGENTS.md` | Source of truth. Codex, Cursor, Copilot, and other AGENTS.md-aware agents |
| `CLAUDE.md` | Claude Code (imports `AGENTS.md` via `@AGENTS.md`, plus Claude-only notes) |
| `.github/copilot-instructions.md` | GitHub Copilot (symlink to `AGENTS.md`) |
| `.claude/settings.json` + `.claude/hooks/` | Claude Code hooks: ruff after each `.py` edit, basedpyright before a turn ends |
| `pyproject.toml` | Reference ruff / basedpyright / pytest config the rules rely on |
| `tools/based8840` | `based8840` CLI: runs every deterministic check in one report |

Edit only `AGENTS.md`; the other instruction files follow it.

## Example

[`examples/library`](examples/library) is a runnable FastAPI + SQLite app that applies every rule in `AGENTS.md`, with a table mapping each rule to the file that shows it. No network access needed.

[`examples/violations`](examples/violations) is a tiny, deliberately broken project: every `based8840 verify --full` step reports at least one finding.

## based8840 CLI

Runs every rule from `AGENTS.md` that a tool can check, and prints one report with each finding tagged by the `AGENTS.md` section it breaks.

```sh
based8840                     # same as `based8840 verify`
based8840 verify [DIR]        # ruff format --check, ruff check, basedpyright, AST rules, pytest
based8840 verify -f [DIR]     # also the opt-in layer checks (--full)
based8840 format [DIR]        # ruff format, nothing else
```

`DIR` defaults to the current directory; the nearest parent with a `pyproject.toml` `[project]` table is checked. `verify` never changes files: unformatted code is reported as a warning. Exit code 0 when everything passes, 1 on any finding, 2 on usage errors.

ruff, basedpyright and pytest run through `uv run` inside the target project, so its own pinned versions and config are used.

On top of ruff and basedpyright, `verify` checks with Python's `ast` (only in `src/`):

| Code | Rule | AGENTS.md |
|---|---|---|
| BC001 | No tuples in parameter or return types | §4 |
| BC002 | Module- and class-level constants are `Final` | §3 |
| BC003 | Direct `BaseModel` subclasses set `ConfigDict(frozen=True, extra="forbid")` | §4 |
| BC004 | No aliases for `Annotated[..., Depends(...)]` | §7 |
| BC005 | Parameters take `Sequence` / `Mapping` / `Set`, not `list` / `dict` / `set` | §3 |
| BC006 | Enums are `StrEnum` with value equal to member name | §3 |
| BC007 | `*State` enums start with `STATE_UNSPECIFIED` | §8 |
| BC008 | A name is bound once per function (sibling branches may each bind it) | §4 |
| BC009 | `noqa` / `pyright: ignore` comments give a reason | §3 |
| BL001 | `--full`: layer import rules (routers, services, DAOs, integrations, domain models) | §7 |
| BL002 | `--full`: services, DAOs and routers never `commit()` | §7 |

Layer checks need exactly one package under `src/`. The report ends with the rules that still need a human reviewer.

Install:

```sh
uv tool install ./tools/based8840                    # puts `based8840` on PATH
uvx --from ./tools/based8840 based8840 verify        # one-off run
uv run --project tools/based8840 based8840 verify examples/library   # inside this repo
```

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
- `py-stop.sh` (Stop): runs `basedpyright` in every project (`pyproject.toml` with `[project]`, up to 3 levels deep, e.g. the repo root or `examples/*`), except `examples/violations`. Errors block the turn once; `stop_hook_active` prevents an endless loop.

Both exit silently when `uv` is missing or the file is not Python. `py-postedit.sh` also skips files in `examples/violations`. Tests are not run in hooks (too slow); `AGENTS.md` requires the agent to run them.

## License

[MIT](LICENSE)
