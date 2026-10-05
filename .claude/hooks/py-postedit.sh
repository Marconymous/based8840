#!/usr/bin/env bash
# PostToolUse hook: format + lint the Python file Claude just edited.
# Exit 2 feeds remaining violations back to Claude.
set -euo pipefail

file_path="$(jq -r '.tool_input.file_path // empty')"

[[ "$file_path" == *.py ]] || exit 0
[[ -f "$file_path" ]] || exit 0
# Broken on purpose (based8840 demo): do not auto-fix it.
[[ "$file_path" == */examples/violations/* ]] && exit 0
command -v uv >/dev/null 2>&1 || exit 0

# Run inside the nearest project (pyproject.toml with a [project] table) so uv finds its tools.
project_dir="$(dirname "$file_path")"
until [[ -f "$project_dir/pyproject.toml" ]] && grep -q '^\[project\]' "$project_dir/pyproject.toml"; do
  [[ "$project_dir" == "/" ]] && exit 0
  project_dir="$(dirname "$project_dir")"
done
cd "$project_dir"

# Lint first so the formatter cleans up after auto-fixes (e.g. removed imports).
lint_status=0
output="$(uv run --quiet ruff check --fix --quiet "$file_path" 2>&1)" || lint_status=$?

uv run --quiet ruff format --quiet "$file_path" || true

if [[ $lint_status -ne 0 ]]; then
  printf 'ruff found violations in %s:\n%s\n' "$file_path" "$output" >&2
  exit 2
fi
