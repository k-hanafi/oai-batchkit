"""User-supplied output schema.

In MVP the user pastes a Pydantic class on the canvas; the frontend serializes
it to a JSON Schema dict and ships it to the backend. The engine never imports
the user's Pydantic model directly — it carries the schema as data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SchemaDef:
    """User-supplied output schema for structured generation."""

    name: str
    json_schema: dict[str, Any]

    @property
    def field_names(self) -> list[str]:
        """Top-level property names from the JSON schema (for CSV column order)."""
        properties = self.json_schema.get("properties") or {}
        if not isinstance(properties, dict):
            return []
        return list(properties.keys())
