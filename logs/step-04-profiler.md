# Step 4: Profiler

## Scope implemented

- Implemented deterministic text-vibe extraction with normalized embeddings.
- Implemented visitor profile aggregation from venue review history.
- Implemented compatibility scoring for free-text preferences and known user IDs.
- Added validation for empty inputs, unknown venues/users, duplicate candidates, and empty histories.
- Added profiler tests against the seeded SQLite database.

## Files changed

- `mcp_servers/profiler_server.py`
- `tests/test_profiler.py`

## Decisions

- Used a fixed vocabulary and standard-library cosine similarity instead of adding heavyweight embedding or topic-model dependencies.
- Returned stable dimension names and normalized vectors so later components can consume the profiler contract deterministically.
- Ranked ties by venue ID after descending score for reproducible orchestration.
- A known user ID is resolved from interaction history; otherwise the input is treated as preference text.
- Empty venue histories produce a neutral profile rather than a fabricated preference signal.

## Validation

- `.venv/bin/python -m pytest tests/test_profiler.py -q` — `7 passed`.
- `.venv/bin/python -m pytest -q` — `18 passed`.

## Remaining risks and follow-up

- The fixed vocabulary is a baseline and does not provide production-grade embeddings or BERTopic representations.
- User IDs and free text share one input contract; future orchestration should make the source explicit where ambiguity matters.
