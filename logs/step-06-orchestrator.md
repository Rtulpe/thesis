# Step 6: Orchestrator

## Scope implemented

- Added the orchestrator flow connecting user state, logistics, profiling, and itinerary tools.
- Added history versus cold-start classification.
- Added city-scoped candidate retrieval and ranked-candidate itinerary delegation.
- Added explainability metadata containing user state, candidate count, compatibility scores, and constraint evidence.
- Added the system prompt contract.
- Added orchestration tests for tool order, cold starts, and invalid input.

## Files changed

- `agent/orchestrator.py`
- `agent/prompts.py`
- `tests/test_orchestrator.py`

## Decisions

- Used a dependency-injected `TravelTools` protocol so orchestration can be tested independently of transport and concrete server implementations.
- Existing users with interaction history are scored by user ID; cold-start users require explicit preference text.
- The orchestrator passes only venues returned for the requested city to the profiler and passes profiler ranking directly to the itinerary engine.
- The orchestrator returns the itinerary engine's result unchanged while adding explainability metadata.
- Kept the system prompt concise and aligned with the five mandatory rules in `PLAN.md`.

## Validation

- `.venv/bin/python -m pytest tests/test_orchestrator.py -q` — `3 passed`.
- `.venv/bin/python -m pytest -q` — `25 passed`.

## Remaining risks and follow-up

- The current implementation uses direct Python tool injection rather than a network MCP transport.
- The final evaluation step should add end-to-end coverage using the concrete SQLite-backed server functions.
