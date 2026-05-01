"""Atomic JSON checkpoint for one Run's pipeline state.

Lifecycle stages per batch:
    prepared -> submitted -> in_progress -> completed | failed | expired | cancelled

The state file is rewritten atomically (write-to-temp then `os.replace`) so a
crash mid-write never corrupts the checkpoint. Every CLI verb is resumable
because state is the single source of truth between invocations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

BatchStatus = Literal[
    "prepared",
    "submitted",
    "in_progress",
    "completed",
    "failed",
    "expired",
    "cancelled",
]


@dataclass
class BatchRecord:
    """One batch's progress through the pipeline.

    Persisted as a member of `PipelineState.batches`. Field names are stable
    across versions of oai-batchkit because old `state.json` files must round-trip
    cleanly through new code.
    """

    batch_number: int
    """1-based ordinal within the run."""

    file_path: str
    """Absolute path to the local JSONL request file."""

    row_range: str
    """Human-readable row range, e.g. '0-4999' or 'retry-37'."""

    estimated_tokens: int = 0
    """Used by the sliding-window queue pressure controller."""

    status: BatchStatus = "prepared"

    file_id: str = ""
    """OpenAI file_id of the uploaded JSONL (set after upload)."""

    batch_id: str = ""
    """OpenAI batch_id (set after `client.batches.create`)."""

    output_file_id: str = ""
    """OpenAI file_id of the result JSONL (set when batch completes)."""

    error_file_id: str = ""
    """OpenAI file_id of the error JSONL, if any."""

    request_count: int = 0
    completed_count: int = 0
    failed_count: int = 0


@dataclass
class PipelineState:
    """Full pipeline state for one run, serialised to `<run_dir>/state.json`."""

    run_id: str = ""
    """Unique identifier for this run instance, e.g. 'oai-batchkit-gpt-5.4-nano-2026-04-30-1605'."""

    task_name: str = ""
    """The `BatchTask.name` of the task that owns this run."""

    model: str = ""
    """OpenAI model snapshot used."""

    params: dict[str, Any] = field(default_factory=dict)
    """Frozen run parameters (mirror of `run.yaml`'s params block)."""

    total_inputs: int = 0
    """Number of input rows the run was prepared for."""

    prompt_fingerprint: str = ""
    """SHA-256 of `task.system_prompt(params)`. Drift detector."""

    dataset_fingerprint: str = ""
    """SHA-256 of the input dataset. Drift detector."""

    pricing_snapshot: dict[str, Any] = field(default_factory=dict)
    """Snapshot of the pricing entry for `model` at run-creation time, so cost
    reports remain reproducible even if the packaged `pricing.json` changes."""

    batches: dict[str, BatchRecord] = field(default_factory=dict)
    """Keyed by JSONL file stem (e.g. 'batch_0001')."""

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cached_tokens: int = 0

    # -- Persistence ----------------------------------------------------------

    def save(self, run_dir: Path) -> None:
        """Atomically write state to `<run_dir>/state.json`.

        Implementation contract: write to a `mkstemp` sibling, then
        `Path.replace` for atomic rename. Never leave a half-written file.
        """
        raise NotImplementedError

    @classmethod
    def load(cls, run_dir: Path) -> PipelineState:
        """Load state from `<run_dir>/state.json`, or return a fresh empty state.

        Tolerant of unknown fields (forward compat) and missing fields
        (backward compat).
        """
        raise NotImplementedError

    # -- Convenience queries --------------------------------------------------

    def pending_batches(self) -> list[BatchRecord]:
        raise NotImplementedError

    def in_flight_batches(self) -> list[BatchRecord]:
        raise NotImplementedError

    def completed_batches(self) -> list[BatchRecord]:
        raise NotImplementedError

    def failed_batches(self) -> list[BatchRecord]:
        raise NotImplementedError

    def estimated_queued_tokens(self) -> int:
        """Sum of `estimated_tokens` across all in-flight batches.

        Used to gate new submissions against OpenAI's 15B-token enqueued cap.
        """
        raise NotImplementedError
