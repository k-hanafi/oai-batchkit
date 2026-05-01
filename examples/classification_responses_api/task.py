"""Example: structured-output classification via the Responses API.

This is the canonical oai-batchkit task shape: one Pydantic schema, one system
prompt, one row formatter. The framework handles every other concern.

Run it (once oai-batchkit's commands are implemented):

    oai-batchkit new examples.classification_responses_api.task:ClassificationTask \\
        --run pilot --params model=gpt-5.4-nano

    oai-batchkit prepare --run pilot --data data/sample.csv --dry-run
    oai-batchkit run     --run pilot --data data/sample.csv
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field

from oai_batchkit.task import BatchTask, Endpoint, InputSource


class ClassificationResult(BaseModel):
    """Output schema. Pydantic + json-schema is the source of truth."""

    CompanyID: str = Field(description="Copied verbatim from input.")
    label: Literal["positive", "neutral", "negative"]
    confidence: int = Field(ge=1, le=5)
    reason: str


class ClassificationTask:
    """A worked example task. Implements the [oai_batchkit.task.BatchTask][] Protocol."""

    name: str = "example-classification"
    endpoint: Endpoint = Endpoint.RESPONSES

    def schema(self, params: Mapping[str, Any]) -> type[BaseModel]:
        return ClassificationResult

    def system_prompt(self, params: Mapping[str, Any]) -> str:
        return (
            "You are an expert reviewer. Read the company description and assign "
            "a sentiment label (positive/neutral/negative) with confidence (1-5) "
            "and a one-sentence reason."
        )

    def cache_key(self, params: Mapping[str, Any]) -> str:
        return f"{self.name}-v1"

    def iter_inputs(
        self, source: InputSource, params: Mapping[str, Any]
    ) -> Iterable[Mapping[str, Any]]:
        yield from source

    def format_user_message(
        self, row: Mapping[str, Any], params: Mapping[str, Any]
    ) -> str:
        return (
            f"CompanyID: {row.get('id', '')}\n"
            f"Description: {row.get('description', '[not available]')}"
        )

    def custom_id(self, row: Mapping[str, Any], params: Mapping[str, Any]) -> str:
        return f"{self.name}-{row['id']}"

    def parse_result(
        self,
        parsed: dict[str, Any],
        raw_response: dict[str, Any],
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        return parsed
