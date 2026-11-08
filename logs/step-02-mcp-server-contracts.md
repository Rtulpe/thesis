# Step 2: MCP Server Contracts

## Scope implemented

- Added the four server modules specified by `PLAN.md`.
- Registered all documented tool names and callable signatures.
- Added a shared dependency-free tool registry for the server adapters.
- Added contract tests for registration and parameter order.

## Files changed

- `mcp_servers/contracts.py`
- `mcp_servers/user_state_server.py`
- `mcp_servers/logistics_server.py`
- `mcp_servers/profiler_server.py`
- `mcp_servers/itinerary_server.py`
- `tests/test_mcp_contracts.py`

## Decisions

- Deferred an MCP SDK dependency. The current step only establishes contracts, and a local registry keeps tests deterministic while preserving a clear integration point for the eventual MCP transport.
- Server functions intentionally raise `NotImplementedError` until their behavior is implemented in Steps 3–6; this prevents silent success-shaped placeholders.
- Kept the exact tool names, parameter names, defaults, and documented return annotations from `PLAN.md`.

## Validation

- `.venv/bin/python -m pytest tests/test_mcp_contracts.py -q` — `2 passed`.
- `.venv/bin/python -m pytest -q` — `4 passed`.

## Remaining risks and follow-up

- The registry is not yet a network-facing MCP transport.
- Logistics, profiler, itinerary, and orchestration behavior are implemented in later steps.
- During Step 7 integration, the user-state contract was backtracked and implemented in
  `mcp_servers/user_state_server.py`; its focused tests and the complete suite pass.
