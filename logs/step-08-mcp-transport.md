# Step 8: MCP Transport

## Scope implemented

- Added MCP SDK transport adapters for all four domain servers.
- Registered the existing domain functions as FastMCP tools without duplicating business logic.
- Added a stdio CLI dispatcher for the user-state, logistics, profiler, and itinerary servers.
- Added transport registration and dispatcher tests.

## Files changed

- `pyproject.toml`
- `mcp_servers/mcp_transport.py`
- `tests/test_mcp_transport.py`

## Decisions

- Added the official `mcp` SDK as a runtime dependency and constrained it to `<2` because the implementation uses the MCP 1.x `FastMCP` API; the unconstrained install resolved to MCP 2.x and failed import compatibility.
- Kept the domain functions and local registry intact so unit tests and in-process orchestration remain available.
- Used stdio as the initial transport because it is supported directly by FastMCP and avoids adding an HTTP deployment layer before the LLM client integration.
- Added explicit server-name dispatch with validation rather than silently selecting a default server.

## Validation

- `.venv/bin/python -m pytest tests/test_mcp_transport.py -q` — `6 passed`.
- `.venv/bin/python -m pytest -q` — `37 passed`.
- Ollama availability checked: `ollama version is 0.30.10`.

## Remaining risks and follow-up

- The MCP transport has not yet been connected to an LLM client.
- HTTP transport and authentication are out of scope for this step.
