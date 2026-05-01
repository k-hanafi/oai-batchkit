"""Pre-flight token counting and cost estimation.

Uses tiktoken for exact token counts and the packaged `pricing.json` (with
project-level override hooks) for per-model rates. Projects total cost with
batch discount and prompt-caching savings so `--dry-run` can surface a full
cost breakdown before any API call.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BATCH_DISCOUNT: float = 0.50
"""OpenAI's documented Batch API discount: 50% off sync rates."""

DEFAULT_CACHE_DISCOUNT: float = 0.50
"""OpenAI's documented prompt-cache discount: cached tokens billed at 50% of input rate.
Stacks with the batch discount, yielding 25% of sync cost for cache-hit input tokens."""


@dataclass(frozen=True)
class CostEstimate:
    """Result of a pre-flight cost estimation.

    Returned by `estimate_cost` and `estimate_from_jsonl`. The
    `format_report` method renders the human-readable breakdown shown by
    `oai-batchkit prepare --dry-run` and `oai-batchkit estimate <jsonl>`.
    """

    model: str
    total_inputs: int
    batches_needed: int

    system_prompt_tokens: int
    schema_tokens: int
    prefix_tokens: int
    avg_user_tokens: int
    total_input_tokens: int
    total_output_tokens: int

    cost_input_sync: float
    cost_output_sync: float
    cost_total_sync: float
    cost_total_batch: float
    cost_with_caching: float

    def format_report(self) -> str:
        """Human-readable cost breakdown suitable for `--dry-run` output."""
        raise NotImplementedError


def load_pricing(override: Path | None = None) -> dict[str, dict[str, float]]:
    """Load the per-model pricing table.

    Reads the packaged `oai-batchkit/pricing.json` by default. If `override` is
    provided, deep-merges it on top of the defaults so projects can pin
    custom rates without forking the package.
    """
    raise NotImplementedError


def count_tokens(text: str, model: str) -> int:
    """Count tokens in `text` using the tiktoken encoding for `model`,
    falling back to `o200k_base` for unknown models."""
    raise NotImplementedError


def estimate_cost(
    system_prompt: str,
    user_messages: Iterable[str],
    model: str,
    batch_size: int,
    *,
    schema_json: str | None = None,
    pricing_override: Path | None = None,
) -> CostEstimate:
    """Count tokens across all requests and project costs.

    Args:
        system_prompt: Full text of the system prompt body.
        user_messages: One formatted user message per input row.
        model: Model name for tokenizer + pricing lookup.
        batch_size: Requests per JSONL file.
        schema_json: Serialized JSON schema (only for structured-output endpoints).
        pricing_override: Optional path to a project-level pricing JSON.

    Returns:
        CostEstimate with full token + cost breakdown.
    """
    raise NotImplementedError


def estimate_from_jsonl(
    jsonl_path: Path,
    *,
    pricing_override: Path | None = None,
) -> CostEstimate:
    """Estimate cost from any pre-built JSONL request file.

    Used by `oai-batchkit estimate <jsonl>` to vet hand-built batch files before
    submission, and by tests to verify the estimator against fixture data.
    """
    raise NotImplementedError
