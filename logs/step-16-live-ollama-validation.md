# Step 16: Live Ollama Tool-Calling Validation

## Scope implemented

- Added an opt-in live validation script targeting Ollama `qwen3.5:4b`.
- Added model-list availability checks through `/api/tags`.
- Added structured `passed`, `skipped`, and `failed` reports.
- Validated MCP tool-schema discovery, tool selection, argument generation, MCP execution, and final response synthesis.
- Added bounded tool rounds and an explicit live timeout to prevent hanging validation runs.

## Files changed

- `scripts/validate_ollama.py`
- `tests/test_live_ollama_validation.py`

## Decisions

- Live validation is not part of the default pytest suite; it is run explicitly through the script.
- Missing Ollama or model availability produces an explicit `skipped` report.
- Runtime/model/tool-calling errors produce a `failed` report and non-zero CLI exit.
- The default prompt requests one appropriate tool call and a concise response to keep validation focused and reproducible.
- Dynamic execution is capped at four rounds for live validation and has a configurable timeout.

## Validation

- `.venv/bin/python -m pytest tests/test_live_ollama_validation.py -q` — `2 passed`.
- Live command:
  `.venv/bin/python -m scripts.validate_ollama --model qwen3.5:4b --timeout-seconds 90`
  — `passed`, `tool_calls: 1`, final response synthesized.
- `.venv/bin/python -m pytest -q` — `63 passed`.

## Remaining risks and follow-up

- Live result quality depends on the selected Ollama model and prompt; validation confirms execution, not recommendation quality.
- The next CLI step should expose the same offline/live selection and report fallback state to users.
