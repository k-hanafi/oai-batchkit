"""Build JSONL batch input files from a CSV dataset.

The builder is endpoint-aware via the Provider: it asks the provider how to
shape each request line and just writes the result. Per-row user messages
come from a `row_to_message` callable supplied by the caller, so the same
builder works for the directness experiment, a customer-support classifier,
or any other tabular -> structured-output task.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from batchkit.domain.batch import BatchRecord
from batchkit.domain.schema import SchemaDef
from batchkit.providers.base import Provider

logger = logging.getLogger(__name__)

DEFAULT_MAX_FILE_SIZE_BYTES: int = 199 * 1024 * 1024

RowToMessage = Callable[[dict[str, object]], str]


def _default_row_to_message(row: dict[str, object]) -> str:
    """Default formatter: stringify the row as JSON."""
    return json.dumps(row, ensure_ascii=False, default=str)


def _build_custom_id(row: dict[str, object], index: int, id_column: str | None) -> str:
    """Stable per-row custom_id used to join results back to inputs."""
    if id_column and id_column in row and row[id_column]:
        return str(row[id_column])
    return f"row-{index:07d}"


def build_batch_files(
    *,
    csv_path: str | Path,
    output_dir: str | Path,
    provider: Provider,
    system_prompt: str,
    schema: SchemaDef,
    model: str,
    batch_size: int,
    row_to_message: RowToMessage | None = None,
    id_column: str | None = None,
    row_slice: slice | None = None,
    max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> list[BatchRecord]:
    """Read the dataset CSV and write provider-shaped JSONL batch files.

    Returns one `BatchRecord` per written file, in `status="prepared"`, ready
    to be handed to the monitor for submission.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    if row_slice is not None:
        df = df.iloc[row_slice]

    formatter = row_to_message or _default_row_to_message
    records: list[BatchRecord] = []
    total_rows = len(df)

    for batch_start in range(0, total_rows, batch_size):
        batch_df = df.iloc[batch_start : batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        file_path = out_dir / f"batch_{batch_num:04d}.jsonl"

        with open(file_path, "w", encoding="utf-8") as f:
            for offset, raw_row in enumerate(batch_df.to_dict(orient="records")):
                row_dict: dict[str, object] = {str(k): v for k, v in raw_row.items()}
                global_index = batch_start + offset
                user_msg = formatter(row_dict)
                custom_id = _build_custom_id(row_dict, global_index, id_column)
                body = provider.format_request_body(
                    custom_id=custom_id,
                    system_prompt=system_prompt,
                    user_message=user_msg,
                    schema=schema,
                    model=model,
                )
                f.write(json.dumps(body, ensure_ascii=False) + "\n")

        file_size = file_path.stat().st_size
        if file_size > max_file_size_bytes:
            raise ValueError(
                f"{file_path.name} is {file_size / 1024 / 1024:.1f} MiB "
                f"(limit {max_file_size_bytes / 1024 / 1024:.1f} MiB). "
                "Reduce batch_size and rebuild."
            )

        row_end = min(batch_start + batch_size - 1, total_rows - 1)
        records.append(
            BatchRecord(
                batch_number=batch_num,
                file_path=str(file_path),
                row_range=f"{batch_start}-{row_end}",
                request_count=len(batch_df),
            )
        )
        logger.info("Wrote %s (%d requests)", file_path.name, len(batch_df))

    return records
