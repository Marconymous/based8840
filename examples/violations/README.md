# violations

Small, deliberately broken project for trying `based8840`. Every step of `based8840 verify --full` reports at least one finding.

```sh
cd examples/violations
uv run --project ../../tools/based8840 based8840 verify --full --atlas-env dev
```

| Step | Where |
|---|---|
| format | `src/app/core/clock.py` (`def  stamp(value:datetime)->str`) |
| lint | `src/app/core/clock.py` (unused import, `print`, naive `datetime.now()`), `src/app/services/orders.py` (nesting, missing return type) |
| types | `src/app/services/orders.py` (wrong return and assignment types, `Any`) |
| rules | `src/app/models/domain/order.py` (non-StrEnum, enum values, state enum, unfrozen model), `src/app/services/orders.py` (tuple return, `list` parameter, missing `Final`, rebinding, ignore comment without reason) |
| config | `pyproject.toml` (`FAST` not selected, `app.models.sql` banned-api entry missing) |
| layers | `src/app/services/orders.py` (imports `app.api`, calls `commit()`) |
| atlas | `migrations/20261005000001_add_note.sql` added without `atlas migrate hash`, so `atlas.sum` does not match |
| tests | `tests/test_orders.py::test_split_order_halves_evenly` |

The Claude Code hooks skip this directory so they don't fix or block on these violations. Don't run `based8840 format` here unless you want to drop the format finding.
