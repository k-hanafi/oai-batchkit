"""End-to-end smoke test for the Phase-1 engine against a MockProvider.

Exercises the full pipeline — build -> submit -> monitor -> download -> merge —
without touching the OpenAI API. The MockProvider's existence is the test of
the Provider Protocol: if it ever drifts out of structural conformance with
`providers.base.Provider`, mypy fails at the call site of `submit_and_monitor`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from batchkit.domain.batch import BatchInfo, RequestCounts
from batchkit.domain.cost import CostEstimate
from batchkit.domain.job import Run
from batchkit.domain.schema import SchemaDef
from batchkit.engine.builder import build_batch_files
from batchkit.engine.downloader import download_completed
from batchkit.engine.merger import merge_batch_csvs
from batchkit.engine.monitor import submit_and_monitor
from batchkit.providers.base import ParsedResult, Provider, Usage


class MockProvider:
    """In-memory provider for tests. Echoes each request as its 'completed' result."""

    name: str = "mock"

    def __init__(self) -> None:
        self._file_counter = 0
        self._batch_counter = 0
        self._files: dict[str, bytes] = {}
        self._batches: dict[str, str] = {}

    def format_request_body(
        self,
        *,
        custom_id: str,
        system_prompt: str,
        user_message: str,
        schema: SchemaDef,
        model: str,
    ) -> dict[str, Any]:
        return {
            "custom_id": custom_id,
            "system_prompt": system_prompt,
            "user_message": user_message,
            "schema_name": schema.name,
            "model": model,
        }

    def parse_result_line(self, line: dict[str, Any]) -> ParsedResult | None:
        usage = line.get("usage") or {}
        return ParsedResult(
            custom_id=str(line["custom_id"]),
            content=dict(line["content"]),
            usage=Usage(
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                cached_tokens=int(usage.get("cached_tokens", 0)),
            ),
        )

    def estimate_cost(
        self,
        *,
        system_prompt: str,
        user_messages: list[str],
        schema: SchemaDef,
        model: str,
        batch_size: int,
    ) -> CostEstimate:
        n = len(user_messages)
        return CostEstimate(
            model=model,
            total_rows=n,
            batches_needed=(n + batch_size - 1) // batch_size,
            system_prompt_tokens=0,
            schema_tokens=0,
            prefix_tokens=0,
            avg_user_tokens=0,
            total_input_tokens=0,
            total_output_tokens=0,
            cost_input_sync=0.0,
            cost_output_sync=0.0,
            cost_total_sync=0.0,
            cost_total_batch=0.0,
            cost_with_caching=0.0,
        )

    async def upload_file(self, file_path: str | Path) -> str:
        self._file_counter += 1
        file_id = f"file-in-{self._file_counter:04d}"
        self._files[file_id] = Path(file_path).read_bytes()
        return file_id

    async def create_batch(
        self,
        *,
        file_id: str,
        model: str,
        run_id: str,
        batch_number: int,
        total_batches: int,
        row_range: str,
    ) -> str:
        self._batch_counter += 1
        batch_id = f"batch-{self._batch_counter:04d}"
        output_file_id = f"file-out-{self._batch_counter:04d}"

        result_lines: list[str] = []
        for raw in self._files[file_id].decode("utf-8").splitlines():
            if not raw.strip():
                continue
            req = json.loads(raw)
            result_lines.append(
                json.dumps(
                    {
                        "custom_id": req["custom_id"],
                        "content": {
                            "echo": req["user_message"],
                            "ok": True,
                        },
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 5,
                            "cached_tokens": 0,
                        },
                    }
                )
            )

        self._files[output_file_id] = ("\n".join(result_lines) + "\n").encode("utf-8")
        self._batches[batch_id] = output_file_id
        return batch_id

    async def retrieve_batch(self, batch_id: str) -> BatchInfo:
        output_file_id = self._batches[batch_id]
        n_lines = sum(
            1 for line in self._files[output_file_id].decode("utf-8").splitlines() if line.strip()
        )
        return BatchInfo(
            batch_id=batch_id,
            status="completed",
            request_counts=RequestCounts(total=n_lines, completed=n_lines, failed=0),
            output_file_id=output_file_id,
            error_file_id=None,
        )

    async def cancel_batch(self, batch_id: str) -> None:
        return None

    async def download_file(self, file_id: str) -> bytes:
        return self._files[file_id]


SCHEMA = SchemaDef(
    name="EchoResult",
    json_schema={
        "type": "object",
        "properties": {
            "echo": {"type": "string"},
            "ok": {"type": "boolean"},
        },
        "required": ["echo", "ok"],
    },
)


def _write_sample_csv(path: Path) -> None:
    path.write_text(
        "id,name\n1,alice\n2,bob\n3,carol\n",
        encoding="utf-8",
    )


async def test_engine_end_to_end_with_mock_provider(tmp_path: Path) -> None:
    csv_path = tmp_path / "input.csv"
    _write_sample_csv(csv_path)

    provider: Provider = MockProvider()

    records = build_batch_files(
        csv_path=csv_path,
        output_dir=tmp_path / "batches",
        provider=provider,
        system_prompt="You are a JSON echo machine.",
        schema=SCHEMA,
        model="mock-model",
        batch_size=2,
        id_column="id",
    )
    assert len(records) == 2
    assert records[0].request_count == 2
    assert records[1].request_count == 1

    run = Run(
        id="run-1",
        job_id="job-1",
        model="mock-model",
        total_rows=3,
        batches={str(r.batch_number): r for r in records},
    )

    events = [
        event
        async for event in submit_and_monitor(
            run=run,
            provider=provider,
            concurrency=2,
            poll_interval_seconds=0.0,
        )
    ]

    assert events, "expected at least one BatchEvent"
    assert all(b.status == "completed" for b in run.batches.values())
    assert {b.batch_id for b in run.batches.values()} == {"batch-0001", "batch-0002"}

    await download_completed(
        run=run,
        provider=provider,
        schema=SCHEMA,
        results_dir=tmp_path / "results",
        errors_dir=tmp_path / "errors",
        csv_dir=tmp_path / "per_batch_csvs",
    )

    assert run.total_prompt_tokens == 30
    assert run.total_completion_tokens == 15
    assert run.total_cached_tokens == 0

    merged_path = tmp_path / "merged.csv"
    merge_batch_csvs(
        run=run,
        schema=SCHEMA,
        input_dir=tmp_path / "per_batch_csvs",
        output_path=merged_path,
    )

    with open(merged_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 3
    assert {row["ok"] for row in rows} == {"True"}
    echoed = {row["echo"] for row in rows}
    assert echoed == {
        '{"id": 1, "name": "alice"}',
        '{"id": 2, "name": "bob"}',
        '{"id": 3, "name": "carol"}',
    }
