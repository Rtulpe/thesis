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
  --database data/user_state.db \
  --cities "Las Vegas,Phoenix" \
  --max-businesses 10000 \
  --max-reviews-per-business 100
```

The importer accepts both generic filenames and Yelp's
`yelp_academic_dataset_*.json` filenames. `--cities` is required for bounded
imports; categories and per-business limits are optional. Tips and check-ins are
not imported. MBTI data is kept separately under `data/raw/mbti` and is not
imported into the tourism database.

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

Profiler embeddings use Ollama's `nomic-embed-text` model when available and cache
vectors in the ignored `data/embeddings.db` file. Offline tests use an explicit
deterministic fallback and expose that fallback in result metadata.

Routing uses a cache-first strategy. Set `OSRM_BASE_URL` to enable OSRM routing;
otherwise, or when OSRM fails, logistics falls back to Haversine estimates:

```bash
export OSRM_BASE_URL=http://localhost:5000
```

Run the opt-in live MCP/Ollama validation:

```bash
.venv/bin/python -m scripts.validate_ollama \
  --model qwen3.5:4b \
  --timeout-seconds 90
```

The validator reports `passed`, `skipped`, or `failed` as JSON. It never makes live
Ollama availability a requirement for the deterministic test suite.

## Command-line interface

Offline deterministic recommendations are the default:

```bash
.venv/bin/python -m agent.cli \
  --user-id new_user \
  --city Amsterdam \
  --start-time 09:00 \
  --end-time 18:00 \
  --preference "history and local culture"
```

Opt into live Ollama/MCP tool calling explicitly:

```bash
.venv/bin/python -m agent.cli \
  --user-id user_demo \
  --city Amsterdam \
  --start-time 09:00 \
  --end-time 18:00 \
  --preference "history and culture" \
  --llm ollama \
  --ollama-model qwen3.5:4b
```

Both modes return JSON. New users are treated as cold-start users when preferences
are provided; unavailable Ollama falls back to offline mode and reports that state.

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

For a single session spanning all four servers, use `MultiServerMCPClient` instead
of `MCPClientSession`. Tools are exposed with names such as
`logistics.get_city_venues` and `itinerary.build_feasible_itinerary`, allowing the
LLM to select a tool without collisions between server namespaces.
## Benchmark evaluation

The evaluation module compares planner callables on the same request set. Each
request must provide `start_time`, `end_time`, and `dwell_time_minutes`; it may
also provide `relevant_venue_ids` and `candidate_venue_ids` for relevance and
coverage metrics.

```python
from evaluation.benchmark_eval import benchmark_methods, write_benchmark_report

report = benchmark_methods(
    requests,
    {
        "dynamic": dynamic_planner,
        "popularity": popularity_planner,
        "random": random_planner,
    },
)
write_benchmark_report(report, "reports/tourism-benchmark.json")
```

The report includes feasibility, constraint violations, relevance, coverage,
latency, visited-venue totals, and optional tool-call totals.
