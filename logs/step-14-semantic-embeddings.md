# Step 14: Semantic Embeddings

## Scope implemented

- Added a provider-neutral embedding protocol and Ollama embedding provider.
- Integrated `nomic-embed-text` through Ollama's `/api/embeddings` endpoint.
- Added a SQLite-backed vector cache with model and text-hash metadata.
- Replaced profiler keyword scoring with cosine similarity over semantic vectors.
- Added deterministic offline embeddings for tests and explicit fallback metadata.
- Added cache reuse, normalization, provider, and profiler integration tests.

## Files changed

- `core/embeddings.py`
- `mcp_servers/profiler_server.py`
- `tests/test_embeddings.py`
- `tests/test_profiler.py`

## Decisions

- Used a swappable `EmbeddingProvider` protocol so another local or remote model can replace Ollama.
- Default live model is `nomic-embed-text`; vectors are L2-normalized for stable cosine scoring.
- Cache keys include item ID, source-text hash, and model name; the cache table is versioned to prevent stale vectors from prior normalization schemes.
- Offline fallback uses the existing deterministic vocabulary provider and returns `fallback: true` rather than silently presenting it as semantic output.
- MBTI remains separate; no personality-classifier training or tourism-table mixing was introduced.

## Validation

- `.venv/bin/python -m pytest tests/test_embeddings.py tests/test_profiler.py -q` — `11 passed`.
- `.venv/bin/python -m pytest -q` — `57 passed`.

## Remaining risks and follow-up

- Live embedding quality depends on the locally installed `nomic-embed-text` model and Ollama availability.
- The profiler retains a compact `dimensions` compatibility field, but semantic ranking is based on the full embedding vector.
