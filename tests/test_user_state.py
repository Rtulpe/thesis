import pytest

from core.database import initialize_database
from mcp_servers import user_state_server


@pytest.fixture
def database_path(tmp_path, monkeypatch):
    path = tmp_path / "user_state.db"
    initialize_database(path, seed=True)
    monkeypatch.setattr(user_state_server, "DATABASE_PATH", path)
    return path


def test_get_user_profile_and_history(database_path):
    profile = user_state_server.get_user_profile("user_demo")
    history = user_state_server.get_user_history("user_demo")

    assert profile["user_id"] == "user_demo"
    assert profile["interaction_count"] == 1
    assert history[0]["venue_id"] == "venue_museum"
    assert "review_text" in history[0]


def test_record_interaction_updates_history(database_path):
    assert user_state_server.record_interaction(
        "user_demo",
        "venue_market",
        4.0,
        "A welcoming local food market.",
    )

    history = user_state_server.get_user_history("user_demo")
    assert len(history) == 2
    assert history[0]["venue_id"] == "venue_market"


def test_user_state_rejects_invalid_inputs(database_path):
    with pytest.raises(ValueError, match="limit"):
        user_state_server.get_user_history("user_demo", limit=0)
    with pytest.raises(ValueError, match="user"):
        user_state_server.get_user_profile("missing")
