"""Merge per-batch CSVs into a single classified output file.

The Rich/Live reporting tables from the source have been removed; this module
just does the CSV concat. Surface-level reporting (distribution tables, cost
breakdown) belongs in the CLI or API layer once Phase 3 lands.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from batchkit.domain.job import Run
from batchkit.domain.schema import SchemaDef

logger = logging.getLogger(__name__)


def merge_batch_csvs(
    *,
    run: Run,
    schema: SchemaDef,
    input_dir: str | Path,
    output_path: str | Path,
) -> Path:
    """Concatenate all per-batch CSVs in batch_number order into one file."""
    in_dir = Path(input_dir)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = schema.field_names
    total_rows = 0

    with open(out_path, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for key in sorted(run.batches, key=lambda k: run.batches[k].batch_number):
            rec = run.batches[key]
            batch_csv = in_dir / f"batch_{rec.batch_number:04d}.csv"
            if not batch_csv.exists():
                logger.warning("Missing per-batch CSV for batch %d; skipping", rec.batch_number)
                continue
            with open(batch_csv, newline="", encoding="utf-8") as in_f:
                reader = csv.DictReader(in_f)
                for row in reader:
                    writer.writerow(row)
                    total_rows += 1

    logger.info("Merged %d rows -> %s", total_rows, out_path.name)
    return out_path
