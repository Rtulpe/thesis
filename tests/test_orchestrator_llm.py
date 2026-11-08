from agent.orchestrator import TravelOrchestrator


class FakeLLM:
    def __init__(self):
        self.calls = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return "Here is your feasible itinerary."


class MinimalTools:
    def get_user_profile(self, user_id):
        return {"user_id": user_id, "review_count": 0}

    def get_user_history(self, user_id, limit=10):
        return []

    def get_city_venues(self, city, category_filter=None, limit=50):
        return [{"venue_id": "venue_museum"}]

    def score_venue_compatibility(self, user_text_or_id, candidate_venue_ids):
        return [{"venue_id": "venue_museum", "score": 1.0}]

    def build_feasible_itinerary(self, candidate_venue_ids, **kwargs):
        return {
            "status": "feasible",
            "total_visited": 1,
            "schedule": [{"venue_id": "venue_museum"}],
            "dropped_venues": [],
        }


def test_orchestrator_can_render_plan_with_llm():
    llm = FakeLLM()
    orchestrator = TravelOrchestrator(MinimalTools(), llm_client=llm)

    result = orchestrator.answer(
        user_id="new_user",
        city="Amsterdam",
        start_time="09:00",
        end_time="18:00",
        preference_text="history",
    )

    assert result["response"] == "Here is your feasible itinerary."
    assert llm.calls[0][0]
    assert "Amsterdam" in llm.calls[0][1]
