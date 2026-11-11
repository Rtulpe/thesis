"""Structured execution traces for agentic planning and repair."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ExecutionTrace:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, event_type: str, **payload: Any) -> None:
        if not event_type or not event_type.strip():
            raise ValueError("event_type must not be empty")
        self._events.append(
            {
                "sequence": len(self._events) + 1,
                "event": event_type,
                **payload,
            }
        )

    def as_dict(self) -> dict[str, Any]:
        return {"events": [dict(event) for event in self._events]}

    def write_json(self, output_path: str | Path) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_dict(), indent=2) + "\n")
