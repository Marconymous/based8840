# violations

Small, deliberately broken project for trying `based8840`. Every step of `based8840 verify --full` reports at least one finding.

```sh
cd examples/violations
uv run --project ../../tools/based8840 based8840 verify --full
```

| Step | Where |
|---|---|
| format | `src/app/core/clock.py` (`def  stamp(value:datetime)->str`) |
| lint | `src/app/core/clock.py` (unused import, `print`, naive `datetime.now()`), `src/app/services/orders.py` (nesting, missing return type) |
| types | `src/app/services/orders.py` (wrong return and assignment types, `Any`) |
| rules | `src/app/models/domain/order.py` (non-StrEnum, enum values, state enum, unfrozen model), `src/app/services/orders.py` (tuple return, `list` parameter, missing `Final`, rebinding, ignore comment without reason) |
| layers | `src/app/services/orders.py` (imports `app.api`, calls `commit()`) |
| tests | `tests/test_orders.py::test_split_order_halves_evenly` |

The Claude Code hooks skip this directory so they don't fix or block on these violations. Don't run `based8840 format` here unless you want to drop the format finding.
