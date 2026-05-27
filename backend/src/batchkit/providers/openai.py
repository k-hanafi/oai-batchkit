"""OpenAI provider adapter.

Implements the `Provider` Protocol against the OpenAI Batch API using the
Responses endpoint (`POST /v1/responses`). Lifted and adapted from
`llm_directness_experiment/src/{submitter,downloader,builder,tokens}.py`,
with three changes:

1. Sync `OpenAI` -> async `AsyncOpenAI`, so the engine's monitor can poll
   N batches concurrently without burning a thread per batch.
2. No state.json / no rich Live UI / no project-local config import — the
   adapter is pure I/O and pure data shaping. The engine drives lifecycle.
3. `format_request_body` and `parse_result_line` are now methods on the
   adapter (the Protocol expects them) so the engine's builder/downloader
   never knows whether the wire shape is Responses, Chat Completions, or
   eventually Anthropic Messages.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any, Literal

import tiktoken
from openai import AsyncOpenAI, BadRequestError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from batchkit.domain.batch import BatchInfo, BatchStatus, RequestCounts
from batchkit.domain.cost import CostEstimate
from batchkit.domain.schema import SchemaDef
from batchkit.engine.tokens import estimate_cost as _engine_estimate_cost
from batchkit.providers.base import ParsedResult, Usage

logger = logging.getLogger(__name__)

OpenAIBatchEndpoint = Literal[
    "/v1/responses",
    "/v1/chat/completions",
    "/v1/embeddings",
    "/v1/completions",
]
OpenAICompletionWindow = Literal["24h"]

DEFAULT_PROMPT_CACHE_KEY: str = "batchkit-default-prompt-cache-key"
DEFAULT_MAX_OUTPUT_TOKENS: int = 800
DEFAULT_RESPONSES_ENDPOINT: OpenAIBatchEndpoint = "/v1/responses"
DEFAULT_COMPLETION_WINDOW: OpenAICompletionWindow = "24h"

MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-5.4-nano": {"input": 0.20, "output": 1.25},
    "gpt-5.4-mini": {"input": 0.40, "output": 1.60},
    "gpt-5.4": {"input": 2.50, "output": 10.00},
}

_OPENAI_STATUS_MAP: dict[str, BatchStatus] = {
    "validating": "submitted",
    "in_progress": "in_progress",
    "finalizing": "in_progress",
    "completed": "completed",
    "failed": "failed",
    "expired": "expired",
    "cancelled": "cancelled",
    "cancelling": "in_progress",
}


class BillingLimitError(RuntimeError):
    """OpenAI returned billing_hard_limit_reached; raise the org cap to resume."""


def _bad_request_error_code(exc: BadRequestError) -> str | None:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            code = err.get("code")
            if isinstance(code, str):
                return code
    text = str(exc).lower()
    if "billing_hard_limit_reached" in text or "billing hard limit" in text:
        return "billing_hard_limit_reached"
    return None


def _patch_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy the schema and set `additionalProperties: false` on every object node.

    OpenAI's strict-mode structured-output requires this on all nested objects.
    Done as a deep copy so the caller's schema isn't mutated.
    """
    patched = copy.deepcopy(schema)

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                node["additionalProperties"] = False
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(patched)
    return patched


def _get_encoding(model: str) -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def _assistant_json_from_response_body(body: dict[str, Any]) -> str | None:
    """Extract the assistant's JSON text from a Responses-API result body.

    Falls back to Chat Completions shape for older batch files.
    """
    out_items = body.get("output")
    if out_items is not None:
        parts: list[str] = []
        for item in out_items:
            if item.get("type") != "message":
                continue
            for block in item.get("content") or []:
                if block.get("type") == "output_text":
                    parts.append(block.get("text") or "")
        text = "".join(parts).strip()
        if text:
            return text

    choices = body.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content
    return None


def _usage_from_response_body(body: dict[str, Any]) -> Usage:
    usage = body.get("usage") or {}
    if "input_tokens" in usage:
        inp_details = usage.get("input_tokens_details") or {}
        return Usage(
            prompt_tokens=int(usage.get("input_tokens") or 0),
            completion_tokens=int(usage.get("output_tokens") or 0),
            cached_tokens=int(inp_details.get("cached_tokens") or 0),
        )
    prompt_details = usage.get("prompt_tokens_details") or {}
    return Usage(
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        cached_tokens=int(prompt_details.get("cached_tokens") or 0),
    )


class OpenAIProvider:
    """OpenAI adapter satisfying `providers.base.Provider`."""

    name: str = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: AsyncOpenAI | None = None,
        prompt_cache_key: str = DEFAULT_PROMPT_CACHE_KEY,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        endpoint: OpenAIBatchEndpoint = DEFAULT_RESPONSES_ENDPOINT,
        completion_window: OpenAICompletionWindow = DEFAULT_COMPLETION_WINDOW,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            self._client = AsyncOpenAI(api_key=api_key) if api_key else AsyncOpenAI()
        self._prompt_cache_key = prompt_cache_key
        self._max_output_tokens = max_output_tokens
        self._endpoint = endpoint
        self._completion_window = completion_window

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
            "method": "POST",
            "url": self._endpoint,
            "body": {
                "model": model,
                "instructions": system_prompt,
                "input": user_message,
                "prompt_cache_key": self._prompt_cache_key,
                "max_output_tokens": self._max_output_tokens,
                "store": False,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": schema.name,
                        "strict": True,
                        "schema": _patch_strict_schema(schema.json_schema),
                    }
                },
            },
        }

    def parse_result_line(self, line: dict[str, Any]) -> ParsedResult | None:
        custom_id = str(line.get("custom_id") or "")
        response = line.get("response") or {}
        body = response.get("body") or {}

        if response.get("status_code") != 200:
            err = line.get("error") or response.get("error") or {}
            logger.warning(
                "Non-200 for %s: %s",
                custom_id,
                err.get("message", "unknown error") if isinstance(err, dict) else err,
            )
            return None

        text = _assistant_json_from_response_body(body)
        if not text:
            logger.warning("No assistant output in response for %s", custom_id)
            return None

        try:
            content = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to JSON-decode assistant output for %s", custom_id)
            return None
        if not isinstance(content, dict):
            logger.warning("Assistant output for %s is not a JSON object", custom_id)
            return None

        return ParsedResult(
            custom_id=custom_id,
            content=content,
            usage=_usage_from_response_body(body),
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
        pricing = MODEL_PRICING.get(model)
        if pricing is None:
            raise ValueError(
                f"No pricing entry for model {model!r}. Known models: {sorted(MODEL_PRICING)}."
            )
        enc = _get_encoding(model)
        return _engine_estimate_cost(
            system_prompt=system_prompt,
            user_messages=user_messages,
            schema=schema,
            model=model,
            batch_size=batch_size,
            max_output_tokens=self._max_output_tokens,
            pricing=pricing,
            encode=lambda s: len(enc.encode(s)),
        )

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def upload_file(self, file_path: str | Path) -> str:
        with open(file_path, "rb") as f:
            response = await self._client.files.create(file=f, purpose="batch")
        logger.info("Uploaded %s -> file_id=%s", Path(file_path).name, response.id)
        return response.id

    @retry(
        retry=retry_if_not_exception_type(BillingLimitError),
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
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
        try:
            batch = await self._client.batches.create(
                input_file_id=file_id,
                endpoint=self._endpoint,
                completion_window=self._completion_window,
                metadata={
                    "run_id": run_id,
                    "batch_number": f"{batch_number}/{total_batches}",
                    "row_range": row_range,
                    "model": model,
                },
            )
        except BadRequestError as e:
            if _bad_request_error_code(e) == "billing_hard_limit_reached":
                raise BillingLimitError(
                    "OpenAI billing hard limit reached (monthly budget cap). "
                    "Raise the limit at "
                    "https://platform.openai.com/settings/organization/limits "
                    "then resume."
                ) from e
            raise
        logger.info(
            "Created batch %s (%s) [%d/%d]",
            batch.id,
            row_range,
            batch_number,
            total_batches,
        )
        return batch.id

    async def retrieve_batch(self, batch_id: str) -> BatchInfo:
        batch = await self._client.batches.retrieve(batch_id)
        status: BatchStatus = _OPENAI_STATUS_MAP.get(batch.status, "in_progress")

        counts = batch.request_counts
        request_counts = RequestCounts(
            total=int(counts.total) if counts and counts.total else 0,
            completed=int(counts.completed) if counts and counts.completed else 0,
            failed=int(counts.failed) if counts and counts.failed else 0,
        )

        return BatchInfo(
            batch_id=batch.id,
            status=status,
            request_counts=request_counts,
            output_file_id=batch.output_file_id,
            error_file_id=batch.error_file_id,
        )

    async def cancel_batch(self, batch_id: str) -> None:
        await self._client.batches.cancel(batch_id)
        logger.info("Cancelled batch %s", batch_id)

    async def download_file(self, file_id: str) -> bytes:
        content = await self._client.files.content(file_id)
        return content.read()
