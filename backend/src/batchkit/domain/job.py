"""Job and Run domain types.

A `Job` is the user's saved configuration (dataset + prompt + schema + model).
A `Run` is one execution of a Job: a collection of `BatchRecord`s plus
aggregate token counters. The store will persist these in Phase 2; for Phase 1
they live in memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from batchkit.domain.batch import BatchRecord
from batchkit.domain.schema import SchemaDef


@dataclass
class Job:
    """Saved configuration for a batch classification task."""

    id: str
    name: str
    dataset_path: str
    system_prompt: str
    schema: SchemaDef
    model: str
    provider: str = "openai"


@dataclass
class Run:
    """One execution of a Job: tracks per-batch progress and aggregate usage."""

    id: str
    job_id: str
    model: str
    total_rows: int = 0
    batches: dict[str, BatchRecord] = field(default_factory=dict)

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cached_tokens: int = 0

    def pending_batches(self) -> list[BatchRecord]:
        return [b for b in self.batches.values() if b.status == "prepared"]

    def in_flight_batches(self) -> list[BatchRecord]:
        return [b for b in self.batches.values() if b.status in ("submitted", "in_progress")]

    def completed_batches(self) -> list[BatchRecord]:
        return [b for b in self.batches.values() if b.status == "completed"]

    def failed_batches(self) -> list[BatchRecord]:
        return [b for b in self.batches.values() if b.status in ("failed", "expired")]

    def estimated_queued_tokens(self) -> int:
        return sum(b.estimated_tokens for b in self.in_flight_batches())
