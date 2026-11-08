import pytest
import math

from core.embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingCache,
    SemanticEmbedder,
)
from core.database import initialize_database
from mcp_servers import profiler_server


class FakeEmbedder:
    model_name = "fake-model"

    def __init__(self):
        self.calls = []

    def embed(self, text):
        self.calls.append(text)
        return [1.0, 0.0] if "history" in text.lower() else [0.0, 1.0]


def test_embedding_cache_persists_vectors_and_model_metadata(tmp_path):
    cache = EmbeddingCache(tmp_path / "embeddings.db")
    cache.put("venue_museum", "history text", "fake-model", [1.0, 0.0])

    assert cache.get("venue_museum", "history text", "fake-model") == [1.0, 0.0]
    assert cache.get("venue_museum", "changed", "fake-model") is None
    assert cache.get("venue_museum", "history text", "other-model") is None


def test_semantic_embedder_uses_cache():
    fake = FakeEmbedder()
    cache = EmbeddingCache(":memory:")
    embedder = SemanticEmbedder(fake, cache)

    assert embedder.embed_for("venue_museum", "history text") == [1.0, 0.0]
    assert embedder.embed_for("venue_museum", "history text") == [1.0, 0.0]
    assert fake.calls == ["history text"]


def test_profiler_uses_injected_semantic_embedder(database_path, monkeypatch):
    fake = FakeEmbedder()
    monkeypatch.setattr(profiler_server, "EMBEDDER", SemanticEmbedder(
        fake, EmbeddingCache(":memory:")
    ))

    result = profiler_server.score_venue_compatibility(
        "history",
        ["venue_museum", "venue_market"],
    )

    assert result[0]["venue_id"] == "venue_museum"
    assert result[0]["embedding_model"] == "fake-model"
    assert result[0]["fallback"] is False


def test_offline_embedder_reports_fallback():
    class FailingProvider:
        model_name = "unavailable"

        def embed(self, text):
            raise RuntimeError("offline")

    embedder = SemanticEmbedder(
        FailingProvider(),
        EmbeddingCache(":memory:"),
        fallback_provider=DeterministicEmbeddingProvider(),
    )

    result = embedder.embed_with_metadata("history and culture")

    assert result["fallback"] is True
    assert result["model"] == "deterministic-v1"
    assert math.sqrt(sum(value * value for value in result["embedding"])) == pytest.approx(
        1.0
    )


@pytest.fixture
def database_path(tmp_path, monkeypatch):
    path = tmp_path / "user_state.db"
    initialize_database(path, seed=True)
    monkeypatch.setattr(profiler_server, "DATABASE_PATH", path)
    return path
