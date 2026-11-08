# Agentic Tourism MCP Recommender

This project implements the agentic tourist recommendation architecture described in
`PLAN.md`. It combines SQLite user state, city-scoped venue logistics, deterministic
vibe matching, feasible itinerary construction, and an orchestration layer.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
```

Initialize a database with representative data:

```bash
.venv/bin/python -c \
  "from core.database import initialize_database; initialize_database('data/user_state.db', seed=True)"
```

## Validation

Run the complete test suite:

```bash
.venv/bin/python -m pytest -q
```

The test suite includes module tests and an end-to-end orchestration test using the
concrete SQLite-backed server functions.

## Architecture

- `core/database.py` creates the user, venue, and interaction schema.
- `mcp_servers/` contains the user-state, logistics, profiler, and itinerary tool
  contracts and implementations.
- `agent/orchestrator.py` coordinates user-state lookup, candidate retrieval,
  compatibility ranking, and itinerary construction.
- `evaluation/` checks itinerary constraints and compares evaluation results.

The current implementation uses dependency-free Python components for deterministic
local development. A network MCP transport can be added around the existing tool
registries without changing the domain contracts.
