# Step 24: Thesis Benchmark Fixtures

## Scope implemented

- Added `evaluation/thesis_fixtures.py`.
- Added deterministic synthetic personas for culture, food, and time-constrained
  travel behavior.
- Added repeated scenarios with compatibility scores, time windows, dwell times,
  mobility mode, distance budgets, and expected violation labels.
- Added a strict-window failure scenario for repair evaluation.

## Important decisions

- Fixtures use an explicit random seed and repetition count for reproducibility.
- Persona records are immutable module-level templates copied into each scenario.
- The fixture layer does not call databases, Ollama, MCP servers, or the solver;
  benchmark runners can execute the same cases against each configuration.
- Current synthetic venue IDs correspond to the seeded application data; later
  dataset-backed fixtures can reuse the same request shape.

## Validation

- `.venv/bin/python -m pytest tests/test_thesis_fixtures.py -q` — `2 passed`.
- `.venv/bin/python -m pytest -q` — `87 passed`.

## Remaining risks and follow-up

- Step 25 must connect these fixtures to direct-LLM, MCP-vector, and full
  OPTW-repair configurations.
- Synthetic compatibility scores are generated labels, not ground truth from a
  human study or imported tourism dataset.
