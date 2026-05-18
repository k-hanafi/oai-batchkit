# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Pre-alpha scaffolding.** The public API surface (CLI commands, type signatures, `BatchTask` protocol, `Run` class) is fully defined and tested. All command/method bodies currently `raise NotImplementedError`. Implementation phases are being added incrementally without breaking the CLI surface.

## Commands

```bash
# Install (editable, with dev dependencies)
pip install -e ".[dev]"

# Run all tests
pytest -q

# Run a single test
pytest tests/test_smoke.py::test_pricing_json_is_packaged_and_well_formed

# Lint and autofix
ruff check --fix src/ tests/
ruff format src/ tests/

# Type check (strict mode)
mypy src/

# Use the CLI
oai-batchkit --help
obk --help            # short alias
```

## Architecture

The framework has three layers:

**1. Plug-in contract (`src/oai_batchkit/task.py`)**  
`BatchTask` is a `runtime_checkable` Protocol. Users implement it (~80 lines) in their own `task.py`. The framework never imports user code at install time — it's dynamically imported at runtime via the module path passed to `oai-batchkit new` (e.g. `mypkg.task:MyTask`). `Endpoint` is an enum for the four supported OpenAI Batch endpoints. `InputSource` is a Protocol wrapping any iterable data source (CSV, JSONL, in-memory).

**2. Public Python API (`src/oai_batchkit/api.py`)**  
`Run` is the central object. Every CLI verb maps 1:1 to a `Run` method. Construct via `Run.create(...)` for new runs or `Run.load(run_dir)` to resume. `RunRegistry.discover(project_root)` finds all runs under `<root>/runs/**` for the `list` command.

**3. Core engine (`src/oai_batchkit/core/`)**  
Internal modules that `Run`'s methods delegate to:
- `builder.py` — builds per-batch JSONL files; injects strict-mode JSON schema (adds `additionalProperties: false` recursively) for structured-output endpoints
- `submitter.py` — uploads files and creates batch jobs via OpenAI API; wraps all calls in tenacity exponential backoff with jitter; raises `BillingLimitError` (not retried) on hard-limit-reached
- `monitor.py` — polling loop with sliding-window queue pressure control (stops at 90% of OpenAI's 15B-token enqueued cap)
- `downloader.py` — fetches result/error files and routes rows through `task.parse_result`
- `merger.py` — concatenates per-batch CSVs into `final.csv`; prints distribution + cost report
- `retry_runner.py` — rebuilds JSONLs from failed `custom_id`s (skips already-completed IDs)
- `tokens.py` — tiktoken-based cost estimation; uses packaged `pricing.json` (deep-merge-overridable per project)
- `state.py` — `PipelineState` + `BatchRecord` dataclasses; `PipelineState.save()` writes atomically via `mkstemp` + `os.replace`

**Supporting modules:**
- `_internal/fingerprint.py` — SHA-256 hashing for prompt + dataset drift detection
- `_internal/lockfile.py` — per-run flock preventing concurrent CLI collisions
- `_internal/logger.py` — rotating `run.log` per run dir
- `notify/` — pluggable notifiers (Slack, email, desktop) for Tier 3 commands

## Run directory layout

Every run owns a directory (default: `./runs/<task_name>/<run_name>/`):

```
<run_dir>/
├── run.yaml         # immutable: task, params, model, batch_size, fingerprints
├── state.json       # atomic checkpoint (PipelineState serialized)
├── run.log          # rotating log
├── lockfile         # flock for concurrent-CLI safety
├── requests/        # batch_NNNN.jsonl  (built by prepare)
├── results/         # batch_NNNN.jsonl  (raw, from OpenAI)
├── errors/          # batch_NNNN_errors.jsonl
├── outputs/         # batch_NNNN.csv    (parsed + validated per task schema)
└── final.csv        # merged output (written by merge)
```

## Implementing a new task

Implement the `BatchTask` protocol (see `examples/classification_responses_api/task.py` for the canonical reference). Key contract rules:
- `format_user_message` must use stable placeholders for missing fields — this preserves the constant prompt prefix required for prompt caching
- `custom_id` must be unique within a run and stable across retries — it's the only join key between async batch results and input rows
- `system_prompt` must be deterministic in `params` — the framework fingerprints it and refuses mid-run drift without `--force`
- `cache_key` should be a stable slug (e.g. `f"{self.name}-v1"`) — bump the version suffix when the system prompt changes

## Pricing and cost estimation

`pricing.json` is a package resource. Structure: `{"discounts": {"batch": 0.5, "cache": 0.5}, "models": {...}}`. Projects can override per-model rates by passing a `pricing_override` path; `load_pricing` deep-merges it on top of defaults. `CostEstimate.cost_with_caching` assumes the system prompt prefix is always cache-hit (best case); actual savings depend on request ordering.

## Key conventions

- `from __future__ import annotations` is used in every module (PEP 563 deferred evaluation)
- mypy runs in strict mode — all public functions need full type annotations
- ruff line length is 100; rule set: E, F, I, B, UP, C4, SIM (E501 ignored)
- Tier 3 CLI commands (`matrix`, `diff`, `notify`, `daemon`, `webhook`) are registered with `hidden=True` — they appear under `--help all` but not default help
