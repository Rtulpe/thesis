# Step 18: Thesis Benchmark Evaluation

## Scope implemented

- Expanded `evaluation/benchmark_eval.py` with `benchmark_methods()`.
- Added shared comparison metrics for dynamic and baseline planners:
  feasibility, constraint validity, constraint violation rate/count, relevance,
  candidate coverage, visited venues, latency, and tool-call totals.
- Added `write_benchmark_report()` for reproducible indented JSON output.
- Added focused tests covering valid and invalid planners, relevance scoring, and
  empty-method validation.

## Important decisions

- Planner callables receive the same request for each method; benchmark-only
  metadata (`relevant_venue_ids` and `candidate_venue_ids`) is removed before
  invocation.
- Constraint validation reuses the existing itinerary evaluator rather than
  duplicating schedule logic.
- Relevance is the fraction of selected venues that occur in
  `relevant_venue_ids`; coverage is selected venues divided by
  `candidate_venue_ids` when that metadata is supplied.
- Planner exceptions remain visible to the caller instead of being converted into
  silent benchmark failures.

## Validation

- `.venv/bin/python -m pytest tests/test_evaluation.py -q` — `4 passed`.
- `.venv/bin/python -m pytest -q` — pending after this step's documentation and
  status updates.

## Remaining risks and follow-up

- A production experiment still needs a dataset-specific request generator and
  explicit relevance labels. The evaluator accepts these labels but does not
  invent them.
- Tool-call totals are read from a planner result's optional `tool_calls` field;
  local deterministic planners may report zero.
