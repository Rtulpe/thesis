# Step 17: User-Facing CLI

## Scope implemented

- Added `agent/cli.py` with an `argparse` interface for user ID, city, time window,
  preferences, category, candidate limit, dwell time, and LLM mode.
- Added deterministic offline mode as the default.
- Added explicit `--llm ollama` opt-in with configurable model and base URL.
- Added structured JSON output containing mode, fallback state, and result.
- Added cold-start support for unknown users when preferences are supplied.
- Added CLI argument and fallback tests.

## Files changed

- `agent/cli.py`
- `tests/test_cli.py`

## Decisions

- Offline deterministic execution is the default and does not require Ollama.
- Ollama mode checks model availability before starting multi-server execution.
- If Ollama is unavailable, the CLI falls back to the deterministic plan and reports
  `fallback: true` with a reason.
- Only an unknown-user error is converted into a cold-start profile; other user-state
  validation errors remain explicit.
- CLI output is JSON so it can be consumed by scripts as well as read in a terminal.

## Validation

- `.venv/bin/python -m pytest tests/test_cli.py -q` — `3 passed`.
- `.venv/bin/python -m pytest -q` — `66 passed`.

## Remaining risks and follow-up

- Ollama mode uses dynamic multi-server tool calling and depends on model behavior;
  Step 16 provides the dedicated live validation path.
- CLI database selection is currently inherited from the server defaults rather than
  exposed as a command-line option.
