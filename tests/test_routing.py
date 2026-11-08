import json

from core.routing import CachedRouter, OSRMRouter


def test_cached_router_returns_stored_route(tmp_path):
    router = CachedRouter(tmp_path / "routing.json")
    router.put(
        "a",
        "b",
        "walking",
        {"distance_meters": 1200, "duration_minutes": 16, "source": "cache"},
    )

    assert router.get("a", "b", "walking")["duration_minutes"] == 16
    assert router.get("b", "a", "walking")["distance_meters"] == 1200


def test_osrm_router_parses_route_response(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {"routes": [{"distance": 1500, "duration": 900}]}
            ).encode()

    monkeypatch.setattr("core.routing.urlopen", lambda request, timeout: Response())
    result = OSRMRouter("http://router").route(
        (4.89, 52.37),
        (4.90, 52.38),
        "walking",
    )

    assert result == {
        "distance_meters": 1500.0,
        "duration_minutes": 15.0,
        "source": "osrm",
    }


def test_osrm_router_raises_on_invalid_response(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"{}"

    monkeypatch.setattr("core.routing.urlopen", lambda request, timeout: Response())

    try:
        OSRMRouter("http://router").route((4.89, 52.37), (4.90, 52.38), "walking")
    except RuntimeError as error:
        assert "route" in str(error)
    else:
        raise AssertionError("Expected malformed routing response to fail")
