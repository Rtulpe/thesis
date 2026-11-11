from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    venue_id: str | None = None
    details: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.venue_id is not None:
            result["venue_id"] = self.venue_id
        if self.details:
            result["details"] = self.details
        return result
