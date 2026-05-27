"""Provider-neutral pre-flight cost estimation.

The math (batch discount, cache discount, prefix-token estimate) lives here.
The tokenizer and the per-model pricing live in the provider — they're
provider-specific. This function takes both as arguments so a different
provider can plug in its own.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from batchkit.domain.cost import CostEstimate
from batchkit.domain.schema import SchemaDef

BATCH_DISCOUNT: float = 0.50
CACHE_DISCOUNT: float = 0.50

Pricing = dict[str, float]
Tokenizer = Callable[[str], int]


def estimate_cost(
    *,
    system_prompt: str,
    user_messages: list[str],
    schema: SchemaDef,
    model: str,
    batch_size: int,
    max_output_tokens: int,
    pricing: Pricing,
    encode: Tokenizer,
    output_estimate_fraction: float = 0.60,
    cache_hit_fraction: float = 0.90,
) -> CostEstimate:
    """Count tokens across all requests and project costs.

    Args:
        system_prompt: Full text of the system prompt.
        user_messages: One per row, already formatted.
        schema: The output schema (counted as part of the cacheable prefix).
        model: Model name (carried into the CostEstimate; pricing is supplied
            separately so the engine stays provider-neutral).
        batch_size: Requests per batch file.
        max_output_tokens: Per-request output cap; used for the conservative
            output projection.
        pricing: Per-1M-token rates with keys "input" and "output".
        encode: Tokenizer function returning token count for a string.
        output_estimate_fraction: How aggressively to size the output projection
            relative to `max_output_tokens` (default 60%).
        cache_hit_fraction: Assumed fraction of prefix tokens that hit cache
            (default 90%, best-case).
    """
    schema_json = json.dumps(schema.json_schema)

    system_toks = encode(system_prompt)
    schema_toks = encode(schema_json)
    prefix_toks = system_toks + schema_toks

    user_tok_counts = [encode(msg) for msg in user_messages]
    avg_user_toks = sum(user_tok_counts) // max(len(user_tok_counts), 1)

    n = len(user_messages)
    total_input = sum(prefix_toks + ut for ut in user_tok_counts)

    est_output_per = int(max_output_tokens * output_estimate_fraction)
    total_output = n * est_output_per

    batches_needed = (n + batch_size - 1) // batch_size

    cost_in = total_input / 1e6 * pricing["input"]
    cost_out = total_output / 1e6 * pricing["output"]
    cost_sync = cost_in + cost_out
    cost_batch = cost_sync * BATCH_DISCOUNT

    prefix_frac = prefix_toks / max(prefix_toks + avg_user_toks, 1)
    cached_toks = int(total_input * prefix_frac * cache_hit_fraction)
    uncached_toks = total_input - cached_toks

    cost_in_cached = (
        uncached_toks / 1e6 * pricing["input"] * BATCH_DISCOUNT
        + cached_toks / 1e6 * pricing["input"] * BATCH_DISCOUNT * CACHE_DISCOUNT
    )
    cost_with_cache = cost_in_cached + cost_out * BATCH_DISCOUNT

    return CostEstimate(
        model=model,
        total_rows=n,
        batches_needed=batches_needed,
        system_prompt_tokens=system_toks,
        schema_tokens=schema_toks,
        prefix_tokens=prefix_toks,
        avg_user_tokens=avg_user_toks,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        cost_input_sync=cost_in,
        cost_output_sync=cost_out,
        cost_total_sync=cost_sync,
        cost_total_batch=cost_batch,
        cost_with_caching=cost_with_cache,
    )
