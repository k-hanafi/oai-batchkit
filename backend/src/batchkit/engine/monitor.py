"""Async concurrent batch monitor.

Submits pending batches with a sliding window (cap on in-flight count) and
polls all in-flight batches concurrently via asyncio.gather. The Rich/Live UI
from the source has been removed: the monitor now yields `BatchEvent`s so
downstream consumers (CLI status display, WebSocket /ws/jobs/{id} in Phase 3)
can render however they like.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from batchkit.domain.batch import BatchEvent, BatchRecord, RequestCounts
from batchkit.domain.job import Run
from batchkit.providers.base import Provider

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_SECONDS: float = 5.0


async def _poll_batch(provider: Provider, record: BatchRecord) -> BatchEvent | None:
    """Poll one batch and update its record in place; return an event if changed."""
    try:
        info = await provider.retrieve_batch(record.batch_id)
    except Exception:
        logger.warning("Failed to poll batch %s", record.batch_id, exc_info=True)
        return None

    record.status = info.status
    record.request_count = info.request_counts.total or record.request_count
    record.completed_count = info.request_counts.completed
    record.failed_count = info.request_counts.failed
    if info.output_file_id:
        record.output_file_id = info.output_file_id
    if info.error_file_id:
        record.error_file_id = info.error_file_id

    return BatchEvent(
        batch_number=record.batch_number,
        batch_id=record.batch_id,
        status=record.status,
        request_counts=info.request_counts,
    )


async def poll_all(run: Run, provider: Provider) -> list[BatchEvent]:
    """Poll every in-flight batch concurrently."""
    in_flight = run.in_flight_batches()
    if not in_flight:
        return []
    results = await asyncio.gather(*[_poll_batch(provider, b) for b in in_flight])
    return [e for e in results if e is not None]


def _can_submit_more(run: Run, concurrency: int, max_queue_tokens: int | None) -> bool:
    """Sliding-window check: do we have room to submit another batch?"""
    if len(run.in_flight_batches()) >= concurrency:
        return False
    return not (
        max_queue_tokens is not None
        and run.estimated_queued_tokens() >= int(max_queue_tokens * 0.90)
    )


async def submit_and_monitor(
    *,
    run: Run,
    provider: Provider,
    concurrency: int = 1,
    estimated_tokens_per_request: int = 0,
    max_queue_tokens: int | None = None,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    total_batches_override: int | None = None,
) -> AsyncIterator[BatchEvent]:
    """Submit and monitor batches until every one is in a terminal state.

    Yields a `BatchEvent` for every submission and every poll observation. The
    caller decides what to do with them (render a progress bar, push to a
    WebSocket, etc).
    """
    total_batches = total_batches_override or len(run.batches)
    logger.info(
        "Starting monitor: %d pending, %d in-flight, concurrency=%d",
        len(run.pending_batches()),
        len(run.in_flight_batches()),
        concurrency,
    )

    while run.pending_batches() or run.in_flight_batches():
        while run.pending_batches() and _can_submit_more(run, concurrency, max_queue_tokens):
            rec = run.pending_batches()[0]
            logger.info("Submitting batch %d ...", rec.batch_number)

            file_id = await provider.upload_file(rec.file_path)
            batch_id = await provider.create_batch(
                file_id=file_id,
                model=run.model,
                run_id=run.id,
                batch_number=rec.batch_number,
                total_batches=total_batches,
                row_range=rec.row_range,
            )

            rec.file_id = file_id
            rec.batch_id = batch_id
            rec.status = "submitted"
            rec.estimated_tokens = estimated_tokens_per_request * max(rec.request_count, 1)

            yield BatchEvent(
                batch_number=rec.batch_number,
                batch_id=rec.batch_id,
                status=rec.status,
                request_counts=RequestCounts(total=rec.request_count),
            )

        for event in await poll_all(run, provider):
            yield event

        if run.in_flight_batches():
            await asyncio.sleep(poll_interval_seconds)

    logger.info(
        "All batches terminal: %d completed, %d failed/expired",
        len(run.completed_batches()),
        len(run.failed_batches()),
    )


async def cancel_run(run: Run, provider: Provider) -> None:
    """Request cancellation for every in-flight batch in a run."""
    in_flight = run.in_flight_batches()
    if not in_flight:
        return
    await asyncio.gather(*[provider.cancel_batch(b.batch_id) for b in in_flight])
