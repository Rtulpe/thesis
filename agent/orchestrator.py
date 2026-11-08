from __future__ import annotations

from typing import Any, Protocol


class TravelTools(Protocol):
    def get_user_profile(self, user_id: str) -> dict[str, Any]: ...

    def get_user_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]: ...

    def get_city_venues(
        self,
        city: str,
        category_filter: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def score_venue_compatibility(
        self,
        user_text_or_id: str,
        candidate_venue_ids: list[str],
    ) -> list[dict[str, Any]]: ...

    def build_feasible_itinerary(
        self,
        candidate_venue_ids: list[str],
        start_time: str,
        end_time: str,
        dwell_time_minutes: int = 90,
        start_location: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class TravelOrchestrator:
    def __init__(self, tools: TravelTools) -> None:
        self._tools = tools

    def plan(
        self,
        user_id: str,
        city: str,
        start_time: str,
        end_time: str,
        *,
        preference_text: str | None = None,
        category_filter: str | None = None,
        candidate_limit: int = 50,
        dwell_time_minutes: int = 90,
        start_location: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not user_id or not user_id.strip():
            raise ValueError("user_id must not be empty")
        if not city or not city.strip():
            raise ValueError("city must not be empty")
        if candidate_limit <= 0:
            raise ValueError("candidate_limit must be greater than zero")

        profile = self._tools.get_user_profile(user_id)
        history = self._tools.get_user_history(user_id)
        has_history = bool(history) and profile.get("review_count", 0) > 0
        user_state = "history" if has_history else "cold_start"
        preference_source = user_id if has_history else preference_text
        if not preference_source:
            raise ValueError(
                "preference_text is required for users without interaction history"
            )

        venues = self._tools.get_city_venues(
            city,
            category_filter=category_filter,
            limit=candidate_limit,
        )
        candidate_ids = [venue["venue_id"] for venue in venues]
        if not candidate_ids:
            raise ValueError(f"No venues found in city: {city}")

        ranked = self._tools.score_venue_compatibility(
            preference_source,
            candidate_ids,
        )
        ranked_ids = [candidate["venue_id"] for candidate in ranked]
        itinerary = self._tools.build_feasible_itinerary(
            ranked_ids,
            start_time=start_time,
            end_time=end_time,
            dwell_time_minutes=dwell_time_minutes,
            start_location=start_location,
        )
        scores = {item["venue_id"]: item["score"] for item in ranked}
        return {
            **itinerary,
            "explanation": {
                "user_state": user_state,
                "city": city,
                "candidate_count": len(candidate_ids),
                "compatibility_scores": scores,
                "selected_venues": [
                    {
                        "venue_id": stop["venue_id"],
                        "compatibility_score": scores.get(stop["venue_id"]),
                        "constraint_evidence": {
                            "arrival_time": stop.get("arrival_time"),
                            "departure_time": stop.get("departure_time"),
                            "binding_reason": stop.get("binding_reason"),
                        },
                    }
                    for stop in itinerary.get("schedule", [])
                ],
            },
        }
