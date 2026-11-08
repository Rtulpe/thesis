# Step 15: Realistic or Cached Routing

## Scope implemented

- Added a persistent local routing-matrix cache.
- Added an OSRM-compatible routing adapter with walking, cycling, and driving profiles.
- Integrated cache-first route lookup into the logistics travel matrix.
- Added explicit Haversine/fixed-speed fallback when OSRM is unavailable or malformed.
- Added routing adapter, cache, fallback, and logistics integration tests.

## Files changed

- `core/routing.py`
- `mcp_servers/logistics_server.py`
- `tests/test_routing.py`
- `tests/test_logistics.py`

## Decisions

- Selected the agreed cache-first strategy: cached route, optional OSRM via `OSRM_BASE_URL`, then Haversine fallback.
- Persisted route data in ignored `data/routing_cache.json`.
- Kept the existing travel-matrix return shape so downstream itinerary behavior remains compatible.
- OSRM failures are handled explicitly by falling back to the deterministic local estimate; no failed remote request is presented as live routing.
- Cache entries are symmetric for reverse venue pairs and keyed by travel mode.

## Validation

- `.venv/bin/python -m pytest tests/test_routing.py tests/test_logistics.py -q` — `10 passed`.
- `.venv/bin/python -m pytest -q` — `61 passed`.

## Remaining risks and follow-up

- No live OSRM endpoint was required for tests; production routing quality depends on configured OSRM data/service.
- The itinerary engine still uses its own Haversine calculation for start-location travel and should be wired to the shared routing adapter in a later refinement.
