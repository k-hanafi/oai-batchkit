"""Pre-flight cost estimate. Provider-neutral data shape."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostEstimate:
    """Result of a pre-flight cost projection across all rows of a job."""

    model: str
    total_rows: int
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
