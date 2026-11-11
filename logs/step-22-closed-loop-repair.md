# Step 22: Closed-Loop Plan Repair

## Scope implemented

- Added `core/repair.py` with a bounded repair policy.
- Re-optimizes the current candidate set before each repair attempt.
- Requests substitutes by machine-readable violation code through an injected
  profiler callback.
- Adds valid, non-duplicate substitutes and their compatibility scores.
- Returns explicit termination states and a structured attempt trace.

## Termination states

- `feasible`: the initial optimization is already valid.
- `repaired`: a later optimization succeeds after substitutions.
- `unrepaired` with `no_substitute`: no valid replacement was supplied.
- `unrepaired` with `max_attempts`: the configured repair bound was reached.

## Important decisions

- The repair policy is dependency-injected and deterministic; it does not require
  an LLM or live MCP process for tests.
- Invalid substitute records are ignored rather than entering the candidate set.
- The policy never mutates the caller's score mapping.
- Live orchestrator wiring and persistent trace storage are deferred to Steps 23
  and later.

## Validation

- `.venv/bin/python -m pytest tests/test_repair.py -q` — `3 passed`.
- `.venv/bin/python -m pytest -q` — `83 passed`.

## Remaining risks and follow-up

- Step 23 should connect this trace shape to multi-round MCP tool invocation logs.
- Substitute retrieval currently depends on the injected callback; the profiler
  integration must define its neighborhood semantics.
