"""Routing adapters with persistent cache and optional OSRM support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class CachedRouter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._routes: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            self._routes = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def _key(source: str, destination: str, mode: str) -> str:
        return f"{source}|{destination}|{mode}"

    def get(self, source: str, destination: str, mode: str) -> dict[str, Any] | None:
        route = self._routes.get(self._key(source, destination, mode))
        return dict(route) if route else None

    def put(
        self,
        source: str,
        destination: str,
        mode: str,
        route: dict[str, Any],
    ) -> None:
        self._routes[self._key(source, destination, mode)] = dict(route)
        self._routes[self._key(destination, source, mode)] = dict(route)
        self.path.write_text(json.dumps(self._routes, indent=2), encoding="utf-8")


class OSRMRouter:
    PROFILE_MAP = {
        "walking": "foot",
        "cycling": "bike",
        "driving": "car",
    }

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def route(
        self,
        source: tuple[float, float],
        destination: tuple[float, float],
        mode: str,
    ) -> dict[str, Any]:
        try:
            profile = self.PROFILE_MAP[mode]
        except KeyError:
            raise ValueError(f"Unsupported routing mode: {mode}") from None
        coordinates = quote(
            f"{source[0]},{source[1]};{destination[0]},{destination[1]}",
            safe=";,",
        )
        request = Request(f"{self.base_url}/route/v1/{profile}/{coordinates}?overview=false")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
            route = body["routes"][0]
            return {
                "distance_meters": float(route["distance"]),
                "duration_minutes": float(route["duration"]) / 60,
                "source": "osrm",
            }
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as error:
            raise RuntimeError(f"OSRM route request failed: {error}") from error
