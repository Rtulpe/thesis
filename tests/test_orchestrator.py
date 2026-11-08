from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent.orchestrator import TravelOrchestrator


@dataclass
class FakeTools:
    calls: list[tuple[str, object]]

    def get_user_profile(self, user_id: str) -> dict:
        self.calls.append(("get_user_profile", user_id))
        return {"user_id": user_id, "review_count": 1}

    def get_user_history(self, user_id: str, limit: int = 10) -> list[dict]:
        self.calls.append(("get_user_history", (user_id, limit)))
        return [{"review_text": "I love history and culture"}]

    def get_city_venues(self, city: str, category_filter=None, limit: int = 50) -> list[dict]:
        self.calls.append(("get_city_venues", (city, category_filter, limit)))
        return [{"venue_id": "venue_museum"}, {"venue_id": "venue_market"}]

    def score_venue_compatibility(self, user_text_or_id: str, candidate_venue_ids: list[str]):
        self.calls.append(("score_venue_compatibility", (user_text_or_id, candidate_venue_ids)))
        return [{"venue_id": "venue_museum", "score": 0.9}]

    def build_feasible_itinerary(self, candidate_venue_ids: list[str], **kwargs):
        self.calls.append(("build_feasible_itinerary", (candidate_venue_ids, kwargs)))
        return {
            "status": "feasible",
            "total_visited": 1,
            "schedule": [{"venue_id": "venue_museum"}],
            "dropped_venues": [],
        }


def test_orchestrator_follows_required_tool_order():
    tools = FakeTools([])
    result = TravelOrchestrator(tools).plan(
        user_id="user_demo",
        city="Amsterdam",
        start_time="09:00",
        end_time="18:00",
    )

    assert [call[0] for call in tools.calls] == [
        "get_user_profile",
        "get_user_history",
        "get_city_venues",
        "score_venue_compatibility",
        "build_feasible_itinerary",
    ]
    assert result["status"] == "feasible"
    assert result["explanation"]["user_state"] == "history"


def test_orchestrator_handles_cold_start_with_preference_text():
    class ColdStartTools(FakeTools):
        def get_user_profile(self, user_id: str) -> dict:
            self.calls.append(("get_user_profile", user_id))
            return {"user_id": user_id, "review_count": 0}

        def get_user_history(self, user_id: str, limit: int = 10) -> list[dict]:
            self.calls.append(("get_user_history", (user_id, limit)))
            return []

    tools = ColdStartTools([])
    result = TravelOrchestrator(tools).plan(
        user_id="new_user",
        city="Amsterdam",
        start_time="09:00",
        end_time="18:00",
        preference_text="quiet history and culture",
    )

    score_call = next(call for call in tools.calls if call[0] == "score_venue_compatibility")
    assert score_call[1][0] == "quiet history and culture"
    assert result["explanation"]["user_state"] == "cold_start"


def test_orchestrator_rejects_empty_city():
    with pytest.raises(ValueError, match="city"):
        TravelOrchestrator(FakeTools([])).plan(
            user_id="user_demo",
            city=" ",
            start_time="09:00",
            end_time="18:00",
        )
