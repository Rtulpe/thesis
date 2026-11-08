import pytest

from core.database import initialize_database
from mcp_servers import profiler_server


@pytest.fixture
def database_path(tmp_path, monkeypatch):
    path = tmp_path / "user_state.db"
    initialize_database(path, seed=True)
    monkeypatch.setattr(profiler_server, "DATABASE_PATH", path)
    return path


def test_extract_text_vibe_is_deterministic_and_normalized():
    first = profiler_server.extract_text_vibe(
        "Thoughtful history exhibits and local culture"
    )
    second = profiler_server.extract_text_vibe(
        "Thoughtful history exhibits and local culture"
    )

    assert first == second
    assert first["dimensions"]["culture"] > 0
    assert first["dimensions"]["history"] > 0
    assert sum(first["embedding"]) == pytest.approx(1.0)


def test_extract_text_vibe_rejects_empty_text():
    with pytest.raises(ValueError, match="text"):
        profiler_server.extract_text_vibe(" ")


def test_get_visitor_profile_aggregates_review_vibes(database_path):
    profile = profiler_server.get_visitor_profile("venue_museum")

    assert profile["venue_id"] == "venue_museum"
    assert profile["review_count"] == 1
    assert profile["dimensions"]["history"] > 0
    assert sum(profile["embedding"]) == pytest.approx(1.0)


def test_get_visitor_profile_rejects_unknown_venue(database_path):
    with pytest.raises(ValueError, match="venue"):
        profiler_server.get_visitor_profile("missing")


def test_score_venue_compatibility_returns_descending_scores(database_path):
    results = profiler_server.score_venue_compatibility(
        "I love history and culture",
        ["venue_market", "venue_museum"],
    )

    assert [item["venue_id"] for item in results] == [
        "venue_museum",
        "venue_market",
    ]
    assert results[0]["score"] >= results[1]["score"]
    assert 0.0 <= results[0]["score"] <= 1.0


def test_score_venue_compatibility_accepts_user_id(database_path):
    results = profiler_server.score_venue_compatibility(
        "user_demo",
        ["venue_museum"],
    )

    assert results[0]["venue_id"] == "venue_museum"
    assert results[0]["score"] == pytest.approx(1.0)


def test_score_venue_compatibility_rejects_empty_candidates(database_path):
    with pytest.raises(ValueError, match="candidate_venue_ids"):
        profiler_server.score_venue_compatibility("history", [])
