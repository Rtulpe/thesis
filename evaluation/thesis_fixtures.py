"""Reproducible synthetic personas and OPTW evaluation scenarios."""

from __future__ import annotations

import random
from typing import Any


PERSONAS: tuple[dict[str, Any], ...] = (
    {
        "persona_id": "culture_explorer",
        "preference_text": "museums history art and local culture",
        "travel_mode": "walking",
        "max_distance": 5000.0,
    },
    {
        "persona_id": "food_traveller",
        "preference_text": "markets restaurants local food and cuisine",
        "travel_mode": "walking",
        "max_distance": 7000.0,
    },
    {
        "persona_id": "time_constrained",
        "preference_text": "highlights with a compact efficient route",
        "travel_mode": "walking",
        "max_distance": 2500.0,
    },
)


def build_thesis_scenarios(
    *,
    seed: int = 42,
    repetitions: int = 1,
) -> list[dict[str, Any]]:
    """Build deterministic scenarios for validity and repair evaluations."""
    if repetitions <= 0:
        raise ValueError("repetitions must be greater than zero")
    randomizer = random.Random(seed)
    scenarios: list[dict[str, Any]] = []
    for repetition in range(repetitions):
        for persona in PERSONAS:
            scores = {
                "venue_museum": round(randomizer.uniform(0.5, 1.0), 6),
                "venue_market": round(randomizer.uniform(0.5, 1.0), 6),
            }
            scenarios.append(
                {
                    "scenario_id": f"{persona['persona_id']}-{repetition + 1}",
                    "persona": dict(persona),
                    "candidate_venue_ids": list(scores),
                    "compatibility_scores": scores,
                    "start_time": "09:00",
                    "end_time": "18:00",
                    "dwell_time_minutes": 90,
                    "expected_violation_codes": [],
                }
            )
        scenarios.append(
            {
                "scenario_id": f"strict-window-{repetition + 1}",
                "persona": dict(PERSONAS[2]),
                "candidate_venue_ids": ["venue_museum"],
                "compatibility_scores": {"venue_museum": 1.0},
                "start_time": "16:00",
                "end_time": "17:00",
                "dwell_time_minutes": 90,
                "expected_violation_codes": ["NO_FEASIBLE_ITINERARY"],
            }
        )
    return scenarios
