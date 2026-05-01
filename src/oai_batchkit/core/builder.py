"""Build per-batch JSONL request files for any of the four Batch API endpoints.

Every JSONL line is a complete OpenAI Batch API request. The static prefix
(model + system prompt + structured-output schema + prompt_cache_key) is
identical across every line in a run, which is the structural prerequisite
for prompt caching. Identical-prefix is guaranteed by construction here, not
by developer discipline downstream.

Endpoint coverage:
  - /v1/responses          : structured outputs via text.format
  - /v1/chat/completions   : structured outputs via response_format
  - /v1/embeddings         : input array per row
  - /v1/moderations        : input string per row
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oai_batchkit.task import BatchTask, Endpoint, Params, Row


def openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively set `additionalProperties: false` on every object node.

    OpenAI's structured-output strict mode requires this on every object,
    but Pydantic's `model_json_schema()` omits it. This walk closes the gap
    without forcing users to hand-author schemas.
    """
    raise NotImplementedError


def build_request_body(
    *,
    endpoint: Endpoint,
    custom_id: str,
    user_message: str,
    system_prompt: str,
    schema: dict[str, Any] | None,
    model: str,
    cache_key: str,
    max_output_tokens: int | None,
) -> dict[str, Any]:
    """Build one JSONL line for the Batch API.

    Routes to per-endpoint body shapes:
      RESPONSES  : `{model, instructions, input, prompt_cache_key, max_output_tokens, store, text.format}`
      CHAT       : `{model, messages: [...], response_format, ...}`
      EMBEDDINGS : `{model, input}`
      MODERATIONS: `{model, input}`
    """
    raise NotImplementedError


def build_batch_files(
    task: BatchTask,
    rows: list[Row],
    params: Params,
    *,
    out_dir: Path,
    model: str,
    batch_size: int,
    max_file_size_mb: int = 190,
    max_output_tokens: int | None = None,
) -> list[Path]:
    """Write `<out_dir>/batch_NNNN.jsonl` files in `batch_size`-sized chunks.

    Warns if any file exceeds `max_file_size_mb` (OpenAI's hard cap is 200 MB).
    Returns the list of written file paths in batch-number order.
    """
    raise NotImplementedError
