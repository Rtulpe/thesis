# Step 10: Dynamic Tool Calling

## Scope implemented

- Added a provider-neutral `ToolCallingLLMClient` protocol.
- Added reflection-based tool schemas for callable tool providers.
- Added bounded multi-round tool execution with normalized results.
- Added unknown-tool and invalid-argument validation.
- Added final natural-language response handling.
- Added Ollama chat-tool request translation and response normalization.
- Added fake-provider tests for tool execution, final responses, and call limits.

## Files changed

- `agent/llm_client.py`
- `agent/orchestrator.py`
- `tests/test_dynamic_tool_calling.py`
- `tests/test_llm_client.py`

## Decisions

- Kept dynamic calling provider-neutral; Ollama is one implementation of the protocol.
- Generated JSON schemas from callable signatures to avoid duplicating tool contracts.
- Limited tool rounds with `max_rounds` to prevent runaway loops.
- Rejected unknown tools and invalid function arguments explicitly.
- Serialized tool results as JSON in conversation messages so Ollama receives valid chat content.
- Backtracked the existing `TravelOrchestrator.plan()` placement after an integration regression and reran the complete suite.

## Validation

- `.venv/bin/python -m pytest tests/test_dynamic_tool_calling.py tests/test_llm_client.py -q` — `6 passed`.
- `.venv/bin/python -m pytest -q` — `44 passed`.

## Remaining risks and follow-up

- No live Ollama tool-calling session was run; this requires a locally pulled model with tool-calling support.
- MCP server processes and the dynamic LLM client are implemented as compatible layers but are not yet connected through an MCP client session.
