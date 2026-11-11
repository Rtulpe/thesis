# Step 25: Thesis Ablation Runner

## Scope implemented

- Added `evaluation/ablation.py`.
- Added shared execution across three required configurations:
  direct LLM, MCP vector retrieval, and OPTW with repair.
- Added common metrics:
  itinerary validity rate, cumulative and mean preference score, mean travel
  time, and mean travel distance.
- Preserved per-scenario results for thesis analysis.

## Important decisions

- Configuration runners are injected callables, allowing deterministic tests and
  later live integrations without coupling the evaluation module to Ollama or MCP.
- Every configuration receives the same scenario object and scenario order.
- Missing required configurations fail explicitly rather than producing a partial
  comparison.
- Validity requires both `status == "feasible"` and an empty violation list.

## Validation

- `.venv/bin/python -m pytest tests/test_ablation.py -q` — `2 passed`.
- `.venv/bin/python -m pytest -q` — `89 passed`.

## Remaining risks and follow-up

- Step 26 should connect concrete runners to the fixture and produce reproducible
  JSON and human-readable thesis reports.
- Direct-LLM and MCP-vector runners are not implemented by this module; they remain
  integration inputs for the final validation step.
