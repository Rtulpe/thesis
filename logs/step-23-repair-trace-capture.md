# Step 23: Repair Trace Capture

## Scope implemented

- Added `core/trace.py` with a JSON-serializable `ExecutionTrace` recorder.
- Added monotonically ordered event sequences.
- Added optional JSON file persistence.
- Integrated optional trace emission into the repair engine for optimizer calls,
  solver results, substitute lookups, substitutions, and termination.
- Preserved the existing repair result trace and API when no recorder is supplied.

## Event types

- `optimizer_call`
- `solver_result`
- `substitute_lookup`
- `substitutes_added`
- `repair_termination`

## Important decisions

- Trace recording is dependency-injected and optional, so existing callers do not
  incur file I/O or receive a changed response shape.
- `ExecutionTrace` stores JSON-compatible payloads and creates parent directories
  when writing a report.
- Live MCP transport and dynamic orchestrator tool events remain unchanged; a later
  integration step can attach this recorder to those boundaries.

## Validation

- `.venv/bin/python -m pytest tests/test_trace.py tests/test_repair.py -q` — `5 passed`.
- `.venv/bin/python -m pytest -q` — `85 passed`.

## Remaining risks and follow-up

- Step 24 should add synthetic personas and failure scenarios that exercise trace
  analysis across multiple repair paths.
- Persistent trace naming/retention policy is not yet defined.
