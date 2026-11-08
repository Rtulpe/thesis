# Agentic Tourism MCP Recommender

This project implements the agentic tourist recommendation architecture described in
`PLAN.md`. It combines SQLite user state, city-scoped venue logistics, deterministic
vibe matching, feasible itinerary construction, and an orchestration layer.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
```

Initialize a database with representative data:

```bash
.venv/bin/python -c \
  "from core.database import initialize_database; initialize_database('data/user_state.db', seed=True)"
```

Import Yelp Open Dataset JSONL files:

```bash
.venv/bin/python -m scripts.import_data \
  --input data/raw/yelp \
  --database data/user_state.db
```

Expected files are `business.json`, `user.json`, and `review.json`. MBTI data is
kept separately under `data/raw/mbti` and is not imported into the tourism database.

## Validation

Run the complete test suite:

```bash
.venv/bin/python -m pytest -q
```

The test suite includes module tests and an end-to-end orchestration test using the
concrete SQLite-backed server functions.

## Architecture

- `core/database.py` creates the user, venue, and interaction schema.
- `mcp_servers/` contains the user-state, logistics, profiler, and itinerary tool
  contracts and implementations.
- `agent/orchestrator.py` coordinates user-state lookup, candidate retrieval,
  compatibility ranking, and itinerary construction.
- `evaluation/` checks itinerary constraints and compares evaluation results.

The current implementation uses dependency-free Python components for deterministic
local development. A network MCP transport can be added around the existing tool
registries without changing the domain contracts.

## MCP transport

The four servers can be run individually over standard input/output:

```bash
.venv/bin/python -m mcp_servers.mcp_transport user-state
.venv/bin/python -m mcp_servers.mcp_transport logistics
.venv/bin/python -m mcp_servers.mcp_transport profiler
.venv/bin/python -m mcp_servers.mcp_transport itinerary
```

The LLM client and dynamic tool-calling layers are planned next and will use these
MCP server processes.

## LLM response generation

Ollama is supported through its local HTTP API:

```bash
export OLLAMA_MODEL=llama3.2
export OLLAMA_BASE_URL=http://localhost:11434
```

`OllamaClient` implements the provider-neutral `LLMClient` protocol. Other
providers can be added by implementing `complete(system_prompt, user_prompt)`.
The current `answer()` method renders an already validated plan; dynamic MCP tool
selection is available through `DynamicToolOrchestrator`.

Dynamic tool calling requires an LLM provider that implements
`complete_with_tools(system_prompt, messages, tools)`. The Ollama implementation
uses the local chat API and limits each request to a configured maximum number of
tool-calling rounds.

## MCP client sessions

The dynamic orchestrator can connect to the actual MCP server processes:

```python
import asyncio

from agent.llm_client import OllamaClient
from agent.mcp_client import MCPClientSession
from agent.orchestrator import DynamicToolOrchestrator


async def main():
    async with MCPClientSession("logistics") as tools:
        result = await DynamicToolOrchestrator(
            tools,
            OllamaClient(),
        ).run_async("Find museums in Amsterdam")
        print(result["response"])


asyncio.run(main())
```

Valid server names are `user-state`, `logistics`, `profiler`, and `itinerary`.
