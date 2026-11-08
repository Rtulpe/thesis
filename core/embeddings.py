"""Embedding providers and a small persistent vector cache."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EmbeddingProvider(Protocol):
    model_name: str

    def embed(self, text: str) -> list[float]: ...


class OllamaEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model_name: str = "nomic-embed-text",
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        request = Request(
            f"{self.base_url}/api/embeddings",
            data=json.dumps({"model": self.model_name, "prompt": text}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Ollama embedding request failed: {error}") from error
        embedding = body.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise RuntimeError("Ollama response did not contain an embedding")
        try:
            return [float(value) for value in embedding]
        except (TypeError, ValueError) as error:
            raise RuntimeError("Ollama embedding contains non-numeric values") from error


class DeterministicEmbeddingProvider:
    model_name = "deterministic-v1"
    _dimensions = ("culture", "history", "food", "nature", "nightlife", "local")
    _terms = {
        "culture": {"culture", "art", "museum", "music", "gallery"},
        "history": {"history", "historic", "heritage", "exhibit", "exhibits"},
        "food": {"food", "restaurant", "market", "taste", "cuisine"},
        "nature": {"nature", "park", "garden", "outdoors", "lake"},
        "nightlife": {"nightlife", "bar", "club", "concert", "party"},
        "local": {"local", "neighborhood", "neighbourhood", "community"},
    }

    def embed(self, text: str) -> list[float]:
        tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        values = [
            float(len(tokens & self._terms[dimension]))
            for dimension in self._dimensions
        ]
        total = sum(values)
        return (
            [value / total for value in values]
            if total
            else [1.0 / len(values)] * len(values)
        )


class EmbeddingCache:
    def __init__(self, path: str | Path) -> None:
        self._connection = sqlite3.connect(path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings_v4 (
                item_id TEXT NOT NULL,
                text_hash TEXT NOT NULL,
                model_name TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                PRIMARY KEY (item_id, text_hash, model_name)
            )
            """
        )
        self._connection.commit()

    def get(self, item_id: str, text: str, model_name: str) -> list[float] | None:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        row = self._connection.execute(
            "SELECT vector_json FROM embeddings_v4 WHERE item_id = ? "
            "AND text_hash = ? AND model_name = ?",
            (item_id, text_hash, model_name),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def put(
        self,
        item_id: str,
        text: str,
        model_name: str,
        vector: list[float],
    ) -> None:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        self._connection.execute(
            "INSERT OR REPLACE INTO embeddings_v4 "
            "(item_id, text_hash, model_name, vector_json) VALUES (?, ?, ?, ?)",
            (item_id, text_hash, model_name, json.dumps(vector)),
        )
        self._connection.commit()


class SemanticEmbedder:
    def __init__(
        self,
        provider: EmbeddingProvider,
        cache: EmbeddingCache,
        *,
        fallback_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.provider = provider
        self.cache = cache
        self.fallback_provider = fallback_provider

    @classmethod
    def offline(cls) -> "SemanticEmbedder":
        provider = DeterministicEmbeddingProvider()
        return cls(provider, EmbeddingCache(":memory:"))

    def embed_for(self, item_id: str, text: str) -> list[float]:
        return self.embed_for_with_metadata(item_id, text)["embedding"]

    def embed_for_with_metadata(self, item_id: str, text: str) -> dict[str, Any]:
        cached = self.cache.get(item_id, text, self.provider.model_name)
        if cached is not None:
            return {
                "embedding": cached,
                "model": self.provider.model_name,
                "fallback": False,
            }
        try:
            vector = self._normalize(self.provider.embed(text))
        except RuntimeError:
            if self.fallback_provider is None:
                raise
            vector = self._normalize(self.fallback_provider.embed(text))
            self.cache.put(item_id, text, self.fallback_provider.model_name, vector)
            return {
                "embedding": vector,
                "model": self.fallback_provider.model_name,
                "fallback": True,
            }
        self.cache.put(item_id, text, self.provider.model_name, vector)
        return {
            "embedding": vector,
            "model": self.provider.model_name,
            "fallback": False,
        }

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        magnitude = sum(value * value for value in vector) ** 0.5
        if magnitude == 0:
            raise RuntimeError("Embedding vector must not be all zero")
        return [value / magnitude for value in vector]

    def embed_with_metadata(self, text: str) -> dict[str, Any]:
        try:
            vector = self._normalize(self.provider.embed(text))
            return {"embedding": vector, "model": self.provider.model_name, "fallback": False}
        except RuntimeError:
            if self.fallback_provider is None:
                raise
            vector = self._normalize(self.fallback_provider.embed(text))
            return {
                "embedding": vector,
                "model": self.fallback_provider.model_name,
                "fallback": True,
            }
