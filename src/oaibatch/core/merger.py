"""Merge per-batch CSVs into one final CSV; print the run's distribution + cost report.

The cost report reconciles the pre-flight estimate against measured usage:
actual prompt-cache hit rate, actual output token count, total spend with
batch + cache discounts applied. This validates the estimator and surfaces
drift early.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oaibatch.core.state import PipelineState


def merge_batch_csvs(
    state: PipelineState,
    run_dir: Path,
    output_path: Path | None = None,
) -> Path:
    """Concatenate `<run_dir>/outputs/batch_NNNN.csv` into one final CSV.

    The output path defaults to `<run_dir>/final.csv`. Preserves the union
    of fieldnames across per-batch CSVs (per-row missing fields fill with
    empty strings).
    """
    raise NotImplementedError


def build_cost_report(
    state: PipelineState,
) -> dict[str, Any]:
    """Compute the measured-cost breakdown.

    Returns a dict with keys: prompt_tokens, completion_tokens, cached_tokens,
    cache_hit_rate, cost_input_uncached, cost_input_cached, cost_output,
    cost_total, predicted_total, drift.
    """
    raise NotImplementedError


def print_report(state: PipelineState, output_path: Path) -> None:
    """Render the merged CSV's distribution table + cost report to the console.

    Distribution rendering is task-specific; tasks may register a custom
    `distribution_table_builder` to surface the columns they care about.
    The default builder shows row count and any Literal-typed schema fields'
    value distributions.
    """
    raise NotImplementedError
