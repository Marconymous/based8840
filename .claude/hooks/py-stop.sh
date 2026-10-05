#!/usr/bin/env bash
# Stop hook: block the turn from ending while basedpyright reports errors.
# Exit 2 feeds the errors back to Claude.
set -euo pipefail

stop_hook_active="$(jq -r '.stop_hook_active // false')"

# Already continued once because of this hook: let the turn end to avoid a loop.
[[ "$stop_hook_active" == "true" ]] && exit 0

project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
command -v uv >/dev/null 2>&1 || exit 0

# Every project (pyproject.toml with a [project] table) in the repo, e.g. the root or examples/*.
# examples/violations is broken on purpose (based8840 demo), so it is skipped.
projects="$(find "$project_dir" -maxdepth 3 -name pyproject.toml \
  -not -path '*/.venv/*' -not -path '*/node_modules/*' \
  -not -path '*/examples/violations/*' \
  -exec grep -l '^\[project\]' {} + 2>/dev/null || true)"

failed=0
for pyproject in $projects; do
  if ! output="$(cd "$(dirname "$pyproject")" && uv run --quiet basedpyright 2>&1)"; then
    printf 'basedpyright failed in %s, fix these before finishing:\n%s\n' \
      "$(dirname "$pyproject")" "$(printf '%s\n' "$output" | tail -n 60)" >&2
    failed=1
  fi
done

[[ $failed -eq 0 ]] || exit 2
