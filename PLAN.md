# Architecture & Implementation Blueprint: Agentic MCP Tourist Recommender

## 1. System Overview & Objectives
This blueprint outlines the architecture for an **Agentic, MCP-driven Tourist Recommendation and Itinerary System**. It serves as a direct follow-up to static tourist recommendation pipelines, addressing historical limitations in:
- Structural cold-start settings and destination-specific ranking.
- Explicit spatial-temporal constraint enforcement (opening hours, travel times, dwell durations).
- Step-by-step faithful explainability across tool execution chains.

The implementation relies on an **LLM Orchestrator** communicating via the **Model Context Protocol (MCP)** across four specialized sub-servers:
1. `User State Server` (Database interaction & history)
2. `Spatial & Logistics Server` (Geography & opening hours)
3. `Personality & Content Profiler Server` (Embeddings & topic/vibe matching)
4. `Constraint & Itinerary Engine Server` (Orienteering Problem / TTDP solver)

---

## 2. System Architecture & Topology

```
+-------------------------------------------------------------------+
|                        LLM Orchestrator                           |
|                  (Agentic Reasoning & Tool Calls)                 |
+-------------------------------------------------------------------+
       |                        |                        |
       | (MCP Protocol)         | (MCP Protocol)         | (MCP Protocol)
       v                        v                        v
+--------------+        +----------------+       +------------------+
|   Server A   |        |    Server B    |       |     Server C     |
| (User State) |        | (Maps/Logistics|       | (Domain Profiler)|
+--------------+        +----------------+       +------------------+
| SQLite/Postgres|       | OpenStreetMap /|       | Vector DB / BERT |
| - Users      |        | Nominatim API  |       | - Vibe/Topics    |
| - History    |        | - Coordinates  |       | - Content Sim    |
| - Ratings    |        | - Distances    |       | - Visitor Profile|
+--------------+        | - Opening Hrs  |       +------------------+
                        +----------------+                |
                                                          v
                                                 +------------------+
                                                 |     Server D     |
                                                 | (Constraint Eng) |
                                                 +------------------+
                                                 | TTDP/OP Solver   |
                                                 | - Time Windows   |
                                                 | - Route Order    |
                                                 +------------------+
```

---

## 3. Data Schema Specifications

### 3.1 Relational DB Schema (`data/user_state.db`)
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    review_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE venues (
    venue_id TEXT PRIMARY KEY,
    name TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    categories TEXT,
    avg_rating REAL,
    opening_hours_json TEXT -- Format: {"mon": ["09:00", "17:00"], ...}
);

CREATE TABLE interactions (
    interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    venue_id TEXT,
    rating REAL,
    review_text TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(venue_id) REFERENCES venues(venue_id)
);
```

---

## 4. MCP Server Definitions & Tool Contracts

### 4.1 Server A: User State Server (`mcp_servers/user_state_server.py`)
Provides access to user histories and raw profile logs.

* **Tools Exposed:**
  * `get_user_profile(user_id: str) -> dict`
    * *Returns:* User metadata and interaction count.
  * `get_user_history(user_id: str, limit: int = 10) -> list[dict]`
    * *Returns:* List of past interactions with venue metadata and review text.
  * `record_interaction(user_id: str, venue_id: str, rating: float, review_text: str) -> bool`

### 4.2 Server B: Spatial & Logistics Server (`mcp_servers/logistics_server.py`)
Handles geographic filtering, travel distance calculations, and real-time open status.

* **Tools Exposed:**
  * `get_city_venues(city: str, category_filter: str = None, limit: int = 50) -> list[dict]`
    * *Returns:* Venues localized to a specific target destination.
  * `calculate_travel_matrix(venue_ids: list[str], travel_mode: str = "walking") -> dict`
    * *Returns:* Square matrix of travel times (in minutes) and distances (in meters) between all requested venues.
  * `check_venue_open_status(venue_id: str, day_of_week: str, time_str: str) -> bool`
    * *Returns:* Boolean indicating whether the venue is open at the specified local time.

### 4.3 Server C: Personality & Profiler Server (`mcp_servers/profiler_server.py`)
Wraps review vector space, BERTopic representations, and visitor-mean compatibility.

* **Tools Exposed:**
  * `extract_text_vibe(text: str) -> dict`
    * *Returns:* Dense embedding vector / topical distribution for input text.
  * `get_visitor_profile(venue_id: str) -> dict`
    * *Returns:* Mean visitor personality/vibe profile calculated from historical review text.
  * `score_venue_compatibility(user_text_or_id: str, candidate_venue_ids: list[str]) -> list[dict]`
    * *Returns:* Ranked candidate venues with cosine compatibility scores $[0.0, 1.0]$.

### 4.4 Server D: Constraint & Itinerary Engine (`mcp_servers/itinerary_server.py`)
Solves the Tourist Trip Design Problem (TTDP) / Orienteering Problem (OP) to build valid routes.

* **Tools Exposed:**
  * `build_feasible_itinerary(candidate_venue_ids: list[str], start_time: str, end_time: str, dwell_time_minutes: int = 90, start_location: dict = None) -> dict`
    * *Input Parameters:*
      * `candidate_venue_ids`: Ranked list of potential venues.
      * `start_time`: e.g., `"10:00"`
      * `end_time`: e.g., `"20:00"`
      * `dwell_time_minutes`: Default duration spent per stop.
    * *Returns:* 
      ```json
      {
        "status": "feasible",
        "total_visited": 4,
        "schedule": [
          {
            "stop_number": 1,
            "venue_id": "v_123",
            "arrival_time": "10:00",
            "departure_time": "11:30",
            "travel_time_from_prev": 0,
            "binding_reason": "Selected high-rank candidate; initial stop."
          }
        ],
        "dropped_venues": ["v_999"]
      }
      ```

---

## 5. Agent Orchestration Loop & System Prompt

### 5.1 Orchestrator Configuration
* **Agent Flow:** ReAct pattern (Reasoning + Action/Tool Execution loop).
* **System Prompt Contract:**

```text
You are an expert AI Travel Planner operating in an Agentic MCP Framework.
Your goal is to build personalized, mathematically feasible day itineraries for tourists.

Follow these strict rules:
1. IDENTIFY USER STATE: Query the User State MCP to determine if the user has an interaction history or is a cold-start user.
2. CANDIDATE RETRIEVAL: Retrieve venues located exclusively within the target destination city using the Logistics MCP.
3. VIBE MATCHING: Score candidates against user preferences using the Profiler MCP.
4. ROUTE OPTIMIZATION: Never build schedules in your head. Pass your top candidate venues to the Itinerary Engine MCP to guarantee opening-hour and travel-budget feasibility.
5. EXPLAINABILITY: Provide step-by-step reasoning for every venue included in the final itinerary, referencing score percentiles, opening constraints, and user preference matches.
```

---

## 6. Project Directory Structure

```text
agentic_tourism_mcp/
├── README.md
├── requirements.txt
├── data/
│   ├── raw_yelp/
│   └── user_state.db
├── mcp_servers/
│   ├── __init__.py
│   ├── user_state_server.py
│   ├── logistics_server.py
│   ├── profiler_server.py
│   └── itinerary_server.py
├── core/
│   ├── __init__.py
│   ├── text_encoder.py
│   ├── ttdp_solver.py
│   └── vector_store.py
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py
│   └── prompts.py
└── evaluation/
    ├── benchmark_eval.py
    └── constraint_test.py
```

---

## 7. Implementation Checklist for Copilot Agents

1. [ ] **Database Setup:** Run script to initialize SQLite schema and seed with subset of venue/user data.
2. [ ] **MCP Server Skeleton:** Implement fastMCP or standard MCP SDK wrappers for the four sub-servers.
3. [ ] **Logistics Functions:** Integrate spatial distance calculations (Haversine or OpenStreetMap routing) and time-window evaluation.
4. [ ] **TTDP Solver Engine:** Build the greedy insertion + 2-opt local search optimization loop for route building inside Server D.
5. [ ] **Agent Loop Integration:** Wire the LLM agent (LangChain / LlamaIndex / AutoGen / custom loop) to interface with all four MCP endpoints.
6. [ ] **Benchmarking:** Implement `evaluation/constraint_test.py` to compare agent constraint violation rates against static recommendation baselines.
## 8. Extended Implementation Steps

8. [ ] **MCP Transport:** Wrap the four server tool registries in actual Model Context Protocol SDK servers and expose them over standard I/O or HTTP.
9. [ ] **LLM Client Integration:** Connect an LLM client to the orchestrator and provide tourism-assistant system instructions.
10. [ ] **Dynamic Tool Calling:** Pass MCP tool schemas to the LLM, execute selected tools dynamically, and build final responses from returned tool results.
11. [ ] **MCP Client Session:** Connect the orchestrator to MCP server processes through SDK client sessions, discover their tools, and execute calls over MCP.

## 9. Thesis-Grade Extensions

The deterministic seed data, keyword profiler, Haversine routing, and greedy itinerary
solver implemented in earlier steps are functional baselines. The following extensions
upgrade those baselines for reproducible thesis evaluation.

12. [ ] **Real Tourism Dataset and Import**
    - Add `scripts/import_data.py` for supported CSV and JSON inputs.
    - Map users, venues, interactions, reviews, ratings, coordinates, categories, and
      opening hours into the existing SQLite schema.
    - Validate required fields, normalize ratings and timestamps, reject malformed
      records with useful diagnostics, and support deterministic reruns.
    - Add import fixtures and integration tests without committing generated databases.

13. [ ] **Multi-Server MCP Orchestration**
    - Manage all four MCP server sessions concurrently in one execution context.
    - Discover and namespace tools without collisions.
    - Preserve user, destination, ranking, and itinerary context across multi-round calls.
    - Close all sessions reliably on success and failure.

14. [ ] **Semantic Embeddings with `nomic-embed-text`**
    - Add an Ollama embedding provider behind a swappable embedding protocol.
    - Replace keyword-only compatibility scoring with cosine similarity over real vectors.
    - Persist or cache venue and user-review embeddings with model/version metadata.
    - Keep a deterministic explicit fallback for offline tests; live embedding tests must
      be opt-in and never silently claim semantic validation.

15. [ ] **Realistic or Cached Routing**
    - Add an OSRM-compatible routing adapter or documented local distance-matrix cache.
    - Support walking and additional configured travel modes where data exists.
    - Preserve a clearly reported Haversine fallback when routing is unavailable.
    - Test cache hits, cache misses, malformed responses, and fallback behavior.

16. [ ] **Live Ollama Tool-Calling Validation**
    - Add an opt-in test/validation script targeting `qwen3.5:4b`.
    - Verify tool-schema interpretation, argument generation, MCP execution, multi-round
      continuation, and final response synthesis.
    - Skip with an explicit reason when Ollama, the model, or a reachable MCP session is
      unavailable; do not make live services mandatory for the deterministic suite.

17. [ ] **User-Facing CLI**
    - Add an `argparse` command accepting user ID, city, start/end times, preferences,
      category, and optional model/server configuration.
    - Return structured itinerary output and readable explanations.
    - Surface configuration, MCP, LLM, and validation errors explicitly with non-zero exits.
    - Add subprocess/CLI tests using fake providers and a deterministic offline mode.

18. [ ] **Thesis Benchmark Framework**
    - Add automated query fixtures and reproducible benchmark execution.
    - Compare the agentic system with random and non-personalized popularity baselines.
    - Report itinerary feasibility, constraint-violation rate, relevance/compatibility,
      venue coverage, dropped-candidate rate, latency, and tool-call counts.
    - Export machine-readable results and a concise human-readable summary.