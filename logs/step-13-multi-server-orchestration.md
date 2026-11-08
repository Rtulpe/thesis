# Step 13: Multi-Server MCP Orchestration

## Scope implemented

- Added `MultiServerMCPClient` for one execution context spanning all four MCP servers.
- Added namespaced tool discovery using `server.tool` names.
- Added concurrent tool-schema discovery and routed calls to the correct server bridge.
- Preserved one shared dynamic-tool conversation context for cross-server calls.
- Added lifecycle tests for discovery, routing, unknown tools, and cleanup.

## Files changed

- `agent/mcp_client.py`
- `tests/test_multi_server_mcp.py`

## Decisions

- All four sessions remain active in one async context; tool discovery runs concurrently after session startup.
- Session context managers are entered sequentially in the owning task because AnyIO cancellation scopes cannot be entered in one task and exited in another. This preserves reliable cleanup while keeping active server sessions concurrent.
- Tool names are namespaced as `user-state.get_user_profile`, `logistics.get_city_venues`, `profiler.score_venue_compatibility`, and `itinerary.build_feasible_itinerary`.
- Unknown namespaced tools fail explicitly rather than being routed by guessing.

## Validation

- `.venv/bin/python -m pytest tests/test_multi_server_mcp.py -q` — `2 passed`.
- Real four-server MCP session discovered `10` tools across:
  `user-state`, `logistics`, `profiler`, and `itinerary`.
- `.venv/bin/python -m pytest -q` — `53 passed`.

## Remaining risks and follow-up

- The dynamic LLM prompt can now receive all namespaced tools, but live qwen3.5:4b multi-server execution remains Step 16 validation.
