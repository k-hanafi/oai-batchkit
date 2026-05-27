"""Batch lifecycle types.

A `BatchRecord` is the engine's mutable view of one batch as it moves through
the pipeline. A `BatchInfo` is a normalized snapshot of what a provider just
told us about a batch (returned from `Provider.retrieve_batch`). A `BatchEvent`
is what the monitor yields each poll for downstream consumers (WebSocket later).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BatchStatus = Literal[
    "prepared",
    "submitted",
    "in_progress",
    "completed",
    "failed",
    "expired",
    "cancelled",
]


@dataclass(frozen=True)
class RequestCounts:
    """How many requests inside one batch have finished."""

    total: int = 0
    completed: int = 0
    failed: int = 0


@dataclass(frozen=True)
class BatchInfo:
    """Normalized snapshot of a batch from any provider.

    Providers translate their own status strings into our `BatchStatus` literal.
    """

    batch_id: str
    status: BatchStatus
    request_counts: RequestCounts = field(default_factory=RequestCounts)
    output_file_id: str | None = None
    error_file_id: str | None = None


@dataclass
class BatchRecord:
    """Engine-owned mutable record of one batch in a run.

    Lifecycle: prepared -> submitted -> in_progress -> (completed | failed | expired | cancelled)
    """

    batch_number: int
    file_path: str
    row_range: str
    estimated_tokens: int = 0
    status: BatchStatus = "prepared"
    file_id: str = ""
    batch_id: str = ""
    output_file_id: str = ""
    error_file_id: str = ""
    request_count: int = 0
    completed_count: int = 0
    failed_count: int = 0


@dataclass(frozen=True)
class BatchEvent:
    """Single observation emitted by the monitor each poll cycle."""

    batch_number: int
    batch_id: str
    status: BatchStatus
    request_counts: RequestCounts
