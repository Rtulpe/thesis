# Step 20: Optimization MCP Contract

## Scope implemented

- Added `optimize_itinerary` to the itinerary server.
- Adapted database venue records, day-specific opening hours, profiler
  compatibility scores, and logistics travel matrices into the isolated OPTW solver.
- Added optional travel mode, maximum distance, and maximum stop constraints.
- Registered the tool in the local itinerary registry and FastMCP transport.
- Preserved `build_feasible_itinerary` as the greedy compatibility baseline.

## Important decisions

- The new tool accepts explicit `compatibility_scores`; score generation remains
  the profiler server's responsibility.
- The initial solver contract uses a zero-cost synthetic start node when no start
  location is provided. Start-location routing remains a later integration item.
- Candidates without opening hours for the requested day are returned as dropped
  venues rather than causing the entire optimization request to fail.
- Existing tool signatures and behavior were not changed.

## Validation

- `.venv/bin/python -m pytest tests/test_itinerary.py tests/test_mcp_contracts.py tests/test_mcp_transport.py -q` — `14 passed`.
- `.venv/bin/python -m pytest -q` — `77 passed`.

## Remaining risks and follow-up

- Step 21 must add structured violation codes to optimization and logistics results.
- The exact solver is intended for bounded candidate sets; callers should enforce
  candidate limits before production-scale optimization.
- Start-location travel must be included before claiming full routing-budget support.
