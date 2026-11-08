# Step 9: LLM Client Integration

## Scope implemented

- Added a provider-agnostic `LLMClient` protocol.
- Added an Ollama chat client using the local `/api/chat` endpoint.
- Added environment configuration for `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.
- Added tourism-assistant response prompts.
- Added `TravelOrchestrator.answer()` to render validated plans through an LLM.
- Added fake-provider and Ollama request/response tests.

## Files changed

- `agent/llm_client.py`
- `agent/orchestrator.py`
- `agent/prompts.py`
- `tests/test_llm_client.py`
- `tests/test_orchestrator_llm.py`

## Decisions

- Used Python's standard-library HTTP client rather than adding an Ollama-specific dependency.
- Kept LLM selection behind the `LLMClient` protocol so Ollama can be replaced by another provider without changing orchestration logic.
- `plan()` remains deterministic and tool-driven; `answer()` adds natural-language rendering only.
- Ollama failures and malformed responses raise explicit `RuntimeError` exceptions.
- Default Ollama configuration is `http://localhost:11434` and model `llama3.2`, both overrideable through constructor arguments or environment variables.

## Validation

- `.venv/bin/python -m pytest tests/test_llm_client.py tests/test_orchestrator_llm.py -q` — `3 passed`.
- `.venv/bin/python -m pytest -q` — `40 passed`.
- Ollama installation confirmed at version `0.30.10`; live model execution was not required for tests.

## Remaining risks and follow-up

- The LLM currently receives a completed itinerary as context; dynamic MCP tool selection is the next step.
- No live Ollama model call was made, so model availability and response quality remain environment-dependent.
