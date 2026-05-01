"""Example: content-safety audit via the Moderations endpoint.

Moderations is free, but Batch-API moderation runs are still useful for
auditing huge corpora because they avoid the synchronous rate-limit
overhead. Same Protocol shape as the embeddings example with a different
endpoint and a different `parse_result`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from oai_batchkit.task import BatchTask, Endpoint, InputSource


class ModerationsTask:
    """Flag every input row that any moderation category triggers."""

    name: str = "example-moderations"
    endpoint: Endpoint = Endpoint.MODERATIONS

    def schema(self, params: Mapping[str, Any]) -> None:
        return None

    def system_prompt(self, params: Mapping[str, Any]) -> str:
        return ""

    def cache_key(self, params: Mapping[str, Any]) -> str:
        return f"{self.name}-v1"

    def iter_inputs(
        self, source: InputSource, params: Mapping[str, Any]
    ) -> Iterable[Mapping[str, Any]]:
        yield from source

    def format_user_message(
        self, row: Mapping[str, Any], params: Mapping[str, Any]
    ) -> str:
        return str(row.get("text", "")).strip()

    def custom_id(self, row: Mapping[str, Any], params: Mapping[str, Any]) -> str:
        return f"{self.name}-{row['id']}"

    def parse_result(
        self,
        parsed: dict[str, Any],
        raw_response: dict[str, Any],
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        results = raw_response.get("results") or []
        first = results[0] if results else {}
        return {
            "flagged": bool(first.get("flagged", False)),
            "categories": first.get("categories", {}),
            "category_scores": first.get("category_scores", {}),
        }
