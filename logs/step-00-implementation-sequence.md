# Implementation Sequence

## Purpose

This log establishes the step boundaries for implementing the architecture in `PLAN.md`. The project currently contains only the plan, so no runtime implementation has been started.

## Numbered steps

1. **Scaffold and database** — Create the project layout, dependency configuration, SQLite schema, and representative seed setup.
2. **MCP server contracts** — Create the four server modules and their MCP tool registrations with the documented signatures and response shapes.
3. **Logistics** — Implement city venue retrieval, travel distance/time calculations, and opening-hours evaluation.
4. **Profiler** — Implement text vibe extraction, visitor profiles, and compatibility ranking using a deterministic, testable vector-store boundary.
5. **Itinerary engine** — Implement feasible time-window scheduling, travel and dwell constraints, and route optimization.
6. **Orchestrator** — Implement the ReAct-style flow and prompts that connect user state, logistics, profiling, and itinerary tools.
7. **Evaluation and documentation** — Add constraint and benchmark evaluations, complete README usage instructions, and run the full validation suite.
8. **MCP transport** — Wrap the four server tool registries in actual Model Context Protocol SDK servers exposed over standard I/O or HTTP.
9. **LLM client integration** — Connect an LLM client to the orchestrator and provide tourism-assistant system instructions.
10. **Dynamic tool calling** — Pass MCP tool schemas to the LLM, execute selected tools dynamically, and produce final responses from tool results.
11. **MCP client session** — Connect the dynamic orchestrator to MCP server processes through SDK client sessions.
12. **Real dataset ingestion** — Parse supported CSV/JSON tourism or review datasets and import users, venues, interactions, coordinates, categories, ratings, reviews, and opening hours reproducibly.
13. **Multi-server orchestration** — Manage user-state, logistics, profiler, and itinerary MCP sessions concurrently and preserve context across tool calls.
14. **Semantic embeddings** — Replace keyword vibe vectors with Ollama `nomic-embed-text` embeddings, with persistent/cacheable venue and user vectors.
15. **Realistic routing** — Add OSRM integration or a local routing-matrix cache with explicit fallback behavior and transit-mode support.
16. **Live Ollama validation** — Add an opt-in validation path using `qwen3.5:4b` that verifies schema selection, argument generation, MCP execution, and final synthesis.
17. **User-facing CLI** — Add an `argparse` CLI accepting user ID, destination, time window, and prompt/preferences and returning the itinerary and explanation.
18. **Thesis benchmarks** — Compare the dynamic agent against random and popularity baselines using feasibility, constraint-violation, relevance, coverage, and latency metrics.

## Decisions

- The seven steps expand the five-item implementation checklist in `PLAN.md` so the profiler and orchestration layers receive explicit implementation and validation boundaries.
- Work proceeds sequentially because later layers depend on earlier contracts and data structures.
- Each completed step gets its own Markdown record in `logs/`; this file remains the sequence-level record.

## Status

- Step 1: Complete.
- Step 2: Complete.
- Step 3: Complete.
- Step 4: Complete.
- Step 5: Complete.
- Step 6: Complete.
- Step 7: Complete.
- Step 8: Complete.
- Step 9: Complete.
- Step 10: Complete.
- Step 11: Complete.
- Step 12: Complete.
- Step 13: Not started.
- Step 14: Not started.
- Step 15: Not started.
- Step 16: Not started.
- Step 17: Not started.
- Step 18: Not started.
