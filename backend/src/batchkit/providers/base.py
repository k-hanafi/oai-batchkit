"""Provider port. Engine talks to anything shaped like this.

A Protocol is a "structural" interface — any class with these methods counts as
a Provider; the implementer never has to inherit from this class. That's what
lets a hand-written MockProvider in a test file substitute for the real OpenAI
adapter with zero coupling between engine and adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from batchkit.domain.batch import BatchInfo
from batchkit.domain.cost import CostEstimate
from batchkit.domain.schema import SchemaDef


@dataclass(frozen=True)
class Usage:
    """Per-response token usage (normalized across providers)."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0


@dataclass(frozen=True)
class ParsedResult:
    """One row's parsed result from a batch output file."""

    custom_id: str
    content: dict[str, Any]
    usage: Usage


class Provider(Protocol):
    """The interface every batch provider must satisfy."""

    name: str

    def format_request_body(
        self,
        *,
        custom_id: str,
        system_prompt: str,
        user_message: str,
        schema: SchemaDef,
        model: str,
    ) -> dict[str, Any]:
        """Build one JSONL line for the batch input file.

        Provider-specific: OpenAI uses `/v1/responses`, Anthropic and Google have
        different wire shapes entirely.
        """
        ...

    def parse_result_line(self, line: dict[str, Any]) -> ParsedResult | None:
        """Parse one JSONL line from a batch output file.

        Returns None for non-200 lines or unparseable content.
        """
        ...

    def estimate_cost(
        self,
        *,
        system_prompt: str,
        user_messages: list[str],
        schema: SchemaDef,
        model: str,
        batch_size: int,
    ) -> CostEstimate:
        """Pre-flight cost projection. Pure compute, no I/O."""
        ...

    async def upload_file(self, file_path: str | Path) -> str:
        """Upload a JSONL batch input file. Returns the provider's file id."""
        ...

    async def create_batch(
        self,
        *,
        file_id: str,
        model: str,
        run_id: str,
        batch_number: int,
        total_batches: int,
        row_range: str,
    ) -> str:
        """Submit a batch job for an uploaded file. Returns the batch id."""
        ...

    async def retrieve_batch(self, batch_id: str) -> BatchInfo:
        """Poll one batch's current state."""
        ...

    async def cancel_batch(self, batch_id: str) -> None:
        """Request cancellation of an in-flight batch."""
        ...

    async def download_file(self, file_id: str) -> bytes:
        """Fetch a result or error file's raw bytes."""
        ...
