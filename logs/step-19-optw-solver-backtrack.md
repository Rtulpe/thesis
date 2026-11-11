# Step 19: OPTW Solver Backend

## Status

Complete. The deterministic optimization backend is implemented and validated.

## Intended scope

- Replace the current greedy itinerary path with a deterministic Time-Window
  Orienteering Problem backend.
- Optimize total profiler compatibility subject to opening hours, travel times,
  dwell times, daily time windows, and hard travel budgets.
- Keep the existing itinerary function available as a compatibility baseline until
  the new solver contract is validated.

## Decisions

- The original itinerary implementation is treated as a baseline rather than the
  thesis novelty claim.
- The solver dependency and exact backend will be selected after inspecting the
  environment and existing dependency manifest.
- Solver work must begin with focused tests and must not silently alter the existing
  MCP tool contract.
- `ortools` and `networkx` are not installed, so the implementation uses an exact
  deterministic branch-and-bound backend without adding a dependency.
- The solver lives in `core/optw_solver.py`; MCP exposure is intentionally deferred
  to Step 20.

## Validation

- `.venv/bin/python -m pytest tests/test_optw_solver.py -q` — `3 passed`.
- `.venv/bin/python -m pytest -q` — `75 passed`.
- Existing itinerary and MCP contracts were not modified.

## Remaining risks

- OR-Tools availability and package footprint must be verified before dependency
  changes.
- The existing database stores venue opening hours but not a full day-specific
  travel matrix for every imported venue; the logistics adapter must provide the
  matrix contract used by optimization.
- The exact search is intended for bounded candidate sets; Step 20 should enforce
  a candidate limit or add a documented solver-size policy.
