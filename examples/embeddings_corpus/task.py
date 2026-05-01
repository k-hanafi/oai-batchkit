"""Example: vectorize a corpus via the Embeddings endpoint at batch pricing.

Embeddings tasks have no system prompt, no JSON schema, and no parsed output
beyond the numeric vector. The Protocol still applies: `format_user_message`
returns the text to embed, `parse_result` decides what to persist (typically
the vector itself plus a row id).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from oai_batchkit.task import BatchTask, Endpoint, InputSource


class EmbeddingsTask:
    """Embed every text row in a corpus and write vectors to a Parquet file."""

    name: str = "example-embeddings"
    endpoint: Endpoint = Endpoint.EMBEDDINGS

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
        data = raw_response.get("data") or []
        vector = data[0]["embedding"] if data else []
        return {"vector": vector}
