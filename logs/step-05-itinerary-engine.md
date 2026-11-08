# Step 5: Itinerary Engine

## Scope implemented

- Implemented feasible itinerary construction for ranked venue candidates.
- Enforced start/end windows, venue opening hours, travel time, and dwell duration.
- Supported optional geographic start locations.
- Returned explicit schedule entries, binding reasons, visit counts, and dropped venues.
- Added focused itinerary tests using the seeded SQLite database.

## Files changed

- `mcp_servers/itinerary_server.py`
- `tests/test_itinerary.py`

## Decisions

- Used a deterministic greedy ranked-candidate strategy as the initial solver; candidates are considered in the profiler-provided order.
- Used Haversine distance and walking speed for travel estimates, matching the current logistics baseline without adding dependencies.
- Used Monday as the current default planning day because the documented itinerary contract has no day-of-week parameter. This should be made explicit in a later contract revision if multi-day planning is required.
- A candidate is dropped when its opening window, travel time, dwell duration, or itinerary end time makes it infeasible.
- A schedule with at least one stop is `feasible`; no valid stops returns `infeasible`.

## Validation

- `.venv/bin/python -m pytest tests/test_itinerary.py -q` — `4 passed`.
- `.venv/bin/python -m pytest -q` — `22 passed`.

## Remaining risks and follow-up

- The current greedy solver does not yet implement the plan's future greedy-insertion plus 2-opt optimization loop.
- Overnight opening windows and explicit planning days are not represented in the current public tool contract.
