"""Download batch result/error files and write per-batch CSVs.

Provider-agnostic: each result line is parsed via `provider.parse_result_line`
so OpenAI Responses vs Chat Completions vs (eventually) Anthropic batch shapes
stay confined to the adapter.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from batchkit.domain.job import Run
from batchkit.domain.schema import SchemaDef
from batchkit.providers.base import Provider

logger = logging.getLogger(__name__)


async def download_completed(
    *,
    run: Run,
    provider: Provider,
    schema: SchemaDef,
    results_dir: str | Path,
    errors_dir: str | Path,
    csv_dir: str | Path,
) -> list[Path]:
    """Download every completed batch's outputs and write per-batch CSVs.

    Updates `run.total_prompt_tokens` / `total_completion_tokens` /
    `total_cached_tokens` in place. Returns the list of written CSV paths.
    """
    results_dir = Path(results_dir)
    errors_dir = Path(errors_dir)
    csv_dir = Path(csv_dir)
    for d in (results_dir, errors_dir, csv_dir):
        d.mkdir(parents=True, exist_ok=True)

    written_csvs: list[Path] = []
    completed = run.completed_batches()

    for rec in completed:
        if rec.error_file_id:
            error_path = errors_dir / f"batch_{rec.batch_number:04d}_errors.jsonl"
            if not error_path.exists():
                error_path.write_bytes(await provider.download_file(rec.error_file_id))

        if not rec.output_file_id:
            logger.warning("Batch %d completed but has no output_file_id", rec.batch_number)
            continue

        result_path = results_dir / f"batch_{rec.batch_number:04d}.jsonl"
        if not result_path.exists():
            result_path.write_bytes(await provider.download_file(rec.output_file_id))

        csv_path = csv_dir / f"batch_{rec.batch_number:04d}.csv"
        prompt_toks, completion_toks, cached_toks = _parse_to_csv(
            result_path=result_path,
            csv_path=csv_path,
            provider=provider,
            schema=schema,
        )

        run.total_prompt_tokens += prompt_toks
        run.total_completion_tokens += completion_toks
        run.total_cached_tokens += cached_toks
        written_csvs.append(csv_path)

        cache_rate = cached_toks / prompt_toks * 100 if prompt_toks > 0 else 0.0
        logger.info(
            "Batch %d: %d prompt toks, %d cached (%.1f%% hit rate)",
            rec.batch_number,
            prompt_toks,
            cached_toks,
            cache_rate,
        )

    return written_csvs


def _parse_to_csv(
    *,
    result_path: Path,
    csv_path: Path,
    provider: Provider,
    schema: SchemaDef,
) -> tuple[int, int, int]:
    """Parse one batch's JSONL result file and write its CSV. Returns token totals."""
    fieldnames = schema.field_names
    prompt_toks = completion_toks = cached_toks = 0
    parsed_count = 0

    with (
        open(result_path, encoding="utf-8") as in_f,
        open(csv_path, "w", newline="", encoding="utf-8") as out_f,
    ):
        writer = csv.DictWriter(out_f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for line_str in in_f:
            line = json.loads(line_str.strip())
            parsed = provider.parse_result_line(line)
            if parsed is None:
                continue
            writer.writerow(parsed.content)
            prompt_toks += parsed.usage.prompt_tokens
            completion_toks += parsed.usage.completion_tokens
            cached_toks += parsed.usage.cached_tokens
            parsed_count += 1

    logger.info("Wrote %d rows -> %s", parsed_count, csv_path.name)
    return prompt_toks, completion_toks, cached_toks
