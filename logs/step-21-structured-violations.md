# Step 21: Structured Violation Contracts

## Scope implemented

- Added the reusable `Violation` value object in `core/violations.py`.
- Added structured violation reports to `optimize_itinerary`.
- Added logistics `validate_travel_budget` with machine-readable distance and
  travel-time budget violations.
- Registered the logistics validation tool through the local registry and FastMCP.
- Preserved the existing boolean `check_venue_open_status` contract.

## Violation codes

- `NO_OPEN_VENUES`
- `NO_FEASIBLE_ITINERARY`
- `TRAVEL_DISTANCE_BUDGET_EXCEEDED`
- `TRAVEL_TIME_BUDGET_EXCEEDED`

Each violation includes a stable `code`, human-readable `message`, and optional
venue or numeric details.

## Important decisions

- Existing successful response fields and legacy tool behavior remain intact.
- Structured violations are additive and intended for the upcoming repair policy.
- Logistics budget validation currently evaluates the aggregate of the supplied
  matrix; route-order-specific validation belongs in the repair/trace work.

## Validation

- Focused Step 21 tests — `25 passed`.
- `.venv/bin/python -m pytest -q` — `80 passed`.

## Remaining risks and follow-up

- Step 22 should consume these codes in a bounded repair loop.
- Opening-hours violations for individual schedule stops should be expanded during
  repair validation if an external route or day-specific constraint changes.
