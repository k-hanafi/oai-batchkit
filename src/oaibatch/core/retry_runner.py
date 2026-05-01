"""Rebuild JSONL request files for failed / expired requests.

Two failure modes are handled distinctly:

  - Per-row failures: error JSONLs from completed batches contain the
    custom_ids that errored. We pull the original request lines out of the
    on-disk request files and split them into new batches.

  - Whole-batch expiry: a batch that hits the 24h completion window without
    finishing returns status `expired`. Its custom_ids are still tracked in
    state but no per-row error file exists; we treat every request in the
    expired batch as eligible for retry.
"""

from __future__ import annotations

from pathlib import Path

from oaibatch.core.state import PipelineState


def rebuild_jsonl_for_failed(
    state: PipelineState,
    failed_custom_ids: set[str],
    run_dir: Path,
    *,
    batch_size: int,
) -> list[Path]:
    """Extract original request lines matching `failed_custom_ids` and write
    them to `<run_dir>/requests/retry_batch_NNNN.jsonl` files.

    Registers each new file as a `BatchRecord` in `state` with status
    `prepared`, so the next `submit` call picks them up automatically.
    Returns the list of new file paths.
    """
    raise NotImplementedError


def expand_expired_batches(state: PipelineState) -> set[str]:
    """For every `expired` batch in `state`, return the union of its custom_ids.

    The CLI's `retry` verb merges this with `collect_failed_custom_ids` so
    a single retry pass covers both failure modes.
    """
    raise NotImplementedError
