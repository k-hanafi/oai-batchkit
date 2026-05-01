"""The BatchTask plug-in protocol and supporting types.

A `BatchTask` is the single integration point a user implements to plug a new
workload into oai-batchkit. The framework owns everything else: file building,
upload, batch creation, sliding-window queue control, polling, download,
parsing, retry, merging, cost reporting.

A "run" is one `(task, params)` cell. The directness experiment's `arm` axis,
for example, is just a key in `params`. The framework treats arms identically
to model variants, prompt variants, dataset slices, or any other experimental
factor.

This module is the canonical place to look for the task-author API. Everything
in `oai_batchkit.core` is internal to the framework.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

Row = Mapping[str, Any]
"""One input record. Whatever shape `iter_inputs` produces; typically a CSV row dict."""

Params = Mapping[str, Any]
"""Frozen run parameters. Any axis the task wants to vary across runs (model, arm,
prompt-version, dataset-slice, etc.) lives in here. Persisted into `run.yaml`."""


class Endpoint(str, Enum):
    """Which OpenAI Batch endpoint a task targets.

    The Batch API supports four endpoints; oai-batchkit is endpoint-agnostic at the
    framework level, so a single task chooses one of these and the builder /
    downloader paths route accordingly.
    """

    RESPONSES = "/v1/responses"
    CHAT = "/v1/chat/completions"
    EMBEDDINGS = "/v1/embeddings"
    MODERATIONS = "/v1/moderations"


@runtime_checkable
class InputSource(Protocol):
    """Anything a task can iterate inputs from.

    Concrete adapters (CSV, JSONL, SQL, in-memory iterable) implement this so
    the framework never has to care about the on-disk format of the dataset.
    """

    def __iter__(self) -> Iterable[Row]:
        """Yield Row dicts in deterministic order."""
        ...

    def __len__(self) -> int:
        """Total row count, for cost estimation and progress reporting."""
        ...


@runtime_checkable
class BatchTask(Protocol):
    """The plug-in contract for a workload.

    All methods receive `params` so a single task implementation can express
    multiple experiment cells. Determinism is the framework's contract with
    the user: given the same `(params, row)` the task must produce the same
    `system_prompt`, `format_user_message`, and `custom_id` outputs.
    """

    name: str
    """Stable identifier; appears in custom_id prefixes, run-dir paths, log lines."""

    endpoint: Endpoint
    """Which OpenAI Batch endpoint this task targets."""

    def schema(self, params: Params) -> type[BaseModel] | None:
        """Pydantic model that defines the structured-output schema, or None.

        For `RESPONSES` / `CHAT` endpoints with structured outputs this is
        injected into the request body via `text.format` (Responses) or
        `response_format` (Chat). For `EMBEDDINGS` / `MODERATIONS` it's None
        because those endpoints have fixed response shapes.
        """
        raise NotImplementedError

    def system_prompt(self, params: Params) -> str:
        """The full system prompt body. Used for cache routing and fingerprinting.

        Must be deterministic in `params`. The framework hashes the return
        value to detect mid-run prompt drift and refuses to mix incompatible
        runs without an explicit `--force`.
        """
        raise NotImplementedError

    def cache_key(self, params: Params) -> str:
        """The OpenAI `prompt_cache_key`. Typically a stable slug derived from
        `name` + a fingerprint of `system_prompt(params)`. Default impls in
        `oai_batchkit.core.builder` compute this for you.
        """
        raise NotImplementedError

    def iter_inputs(self, source: InputSource, params: Params) -> Iterable[Row]:
        """Materialize input rows from `source` into the shape this task expects.

        The default behavior is to forward `source` unchanged; tasks override
        this to filter, sort, deduplicate, or join with auxiliary data.
        """
        raise NotImplementedError

    def format_user_message(self, row: Row, params: Params) -> str:
        """Render one input row as the user-message string for the prompt.

        Output goes verbatim into `body.input` (Responses) or
        `body.messages[-1].content` (Chat). Empty / missing fields should be
        rendered with a stable placeholder so the prompt's INPUT FORMAT block
        remains uniform across rows (this enables prompt caching).
        """
        raise NotImplementedError

    def custom_id(self, row: Row, params: Params) -> str:
        """Stable `custom_id` for this row. Must be unique within a run.

        The custom_id is the only key joining async batch results back to
        their input row, since batch output order is not guaranteed. A
        common pattern is `f"{self.name}-{row['id']}"`.
        """
        raise NotImplementedError

    def parse_result(
        self, parsed: dict[str, Any], raw_response: dict[str, Any], params: Params
    ) -> dict[str, Any]:
        """Post-process one validated response into the row written to per-batch CSV.

        `parsed` is the JSON content already validated against `schema()`.
        `raw_response` is the full Batch API response body (gives access to
        usage stats, finish reason, etc.). The default implementation returns
        `parsed` unchanged.
        """
        raise NotImplementedError
