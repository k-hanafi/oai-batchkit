# AGENTS.md

Instructions for AI coding agents working in this repository (Cursor, Claude Code, Codex, GitHub Copilot, cloud agents). **Read this file before making changes.**

This file is the single source of truth for agent behavior in `oai-batchkit`. It replaces project-specific Cursor Settings rules so the same context applies regardless of which tool you use. **You should not need to explore the whole repo to understand what exists, what's planned, or how pieces connect** — that context lives here.

---

## Repository briefing

### What this project is

**oai-batchkit** is a toolkit for running large-scale LLM jobs via provider batch APIs (OpenAI Batch API first). It handles the full pipeline researchers otherwise rebuild every time:

1. **Prepare** — CSV → valid batch JSONL input files (respecting file size limits)
2. **Estimate** — pre-flight token and cost projection (sync vs batch pricing, prompt caching)
3. **Submit** — upload files, create batches, manage concurrency and queue-pressure limits
4. **Monitor** — poll in-flight batches concurrently, emit progress events
5. **Recover** — retry failed/expired rows without restarting the whole run
6. **Merge** — combine per-batch CSVs into one final output table with schema columns

**Origin:** Extracted from two research repos after building the same pipeline three times:
- [llm_directness_experiment](https://github.com/k-hanafi/llm_directness_experiment) — original batch engine source code
- [ai-native-startup-classification](https://github.com/k-hanafi/ai-native-startup-classification) — 280k-startup taxonomy classification at scale

**Direction:** Rebuilding from a Python CLI into an **Electron + React + FastAPI desktop app** with a React Flow canvas so non-engineer researchers can run batch jobs visually. The CLI survives as a second client of the same engine.

### Current build status

| Phase | What | Status |
|-------|------|--------|
| 0 | Monorepo scaffold (`backend/`, `frontend/`, `shell/`), CI, pre-commit | **Done** |
| 1 | Engine port: domain types, `Provider` protocol, OpenAI adapter, smoke test | **Done** |
| 2 | SQLite store (SQLAlchemy 2.0 async, JobRepo/RunRepo/BatchRepo) | **Next** |
| 3 | FastAPI REST + WebSocket | Pending |
| 4 | Background poller daemon | Pending |
| 5 | React frontend foundation (React Query, WS hook) | Pending |
| 6 | React Flow canvas (4 node types) | Pending |
| 7 | Electron shell + macOS packaging | Pending |
| 8 | Ship DMG + docs | Pending |

Full phased plan with architecture diagrams and design rationale: [`plans/batchkit-mvp-architecture_4b392a9e.plan.md`](plans/batchkit-mvp-architecture_4b392a9e.plan.md)

### Tech stack

| Layer | Stack | Notes |
|-------|-------|-------|
| Backend | Python 3.11+, FastAPI (Phase 3), Pydantic 2, SQLAlchemy 2.0 async (Phase 2) | `ruff`, `mypy --strict`, `pytest`, `pytest-asyncio` |
| Engine deps | `openai` (AsyncOpenAI), `tenacity`, `tiktoken`, `pandas` | Engine itself has no FastAPI/SQLAlchemy imports |
| Frontend | Vite 6, React 18, TypeScript 5.6, Tailwind 3 | React Flow, React Query, Monaco, shadcn/ui come in Phases 5–6 |
| Shell | Electron + electron-forge | Phase 7: spawn Python backend subprocess, macOS code signing |
| CI | GitHub Actions | Separate jobs for backend, frontend, shell (`.github/workflows/ci.yml`) |
| DB | SQLite via SQLAlchemy | No Alembic in MVP — `create_all()` at startup |

**Target platform:** macOS only for MVP.

### Architecture

```
Electron shell (main process)
  └─ React canvas (renderer) ──HTTP/WS──► FastAPI (Phase 3)
                                              │
                                         Engine (pure)
                                         /    |    \
                                   Provider  Store  (Clock)
                                   (OpenAI)  (SQLite)
                                              │
                                         Daemon poller (Phase 4)

Typer CLI (Phase 3+) ──► same Engine
```

**Hexagonal / ports-and-adapters — non-negotiable:**

1. `backend/src/batchkit/domain/` and `engine/` must **never** import FastAPI, SQLAlchemy, OpenAI SDK, or React. They depend on Protocols (`Provider`, `Store`, `Clock`).
2. Job state lives in **SQLite from day 1**, not JSON files (Phase 2 replaces in-memory `Run` persistence).
3. OpenAI is the only provider in MVP. Anthropic/Google = new files in `providers/`, not engine refactors.
4. The CLI and GUI are **two clients of the same Engine** — not separate code paths.

---

## What exists today (file map)

### Backend — `backend/src/batchkit/`

```
batchkit/
  domain/           Pure dataclasses — no I/O, no framework imports
    job.py          Job (saved config), Run (one execution + token counters)
    batch.py        BatchStatus, BatchRecord, BatchInfo, BatchEvent, RequestCounts
    schema.py       SchemaDef (user's JSON schema as data, not imported Pydantic)
    cost.py         CostEstimate (pre-flight projection result)

  engine/           Pure pipeline logic — takes Provider + in-memory Run
    builder.py      CSV → JSONL batch files via provider.format_request_body()
    monitor.py      Async submit + poll loop; yields BatchEvent (no Rich UI)
    downloader.py   Fetch completed batch outputs → per-batch CSVs
    merger.py       Combine per-batch CSVs → one merged output
    tokens.py       Token counting + cost math (tiktoken)

  providers/
    base.py         Provider Protocol + ParsedResult + Usage
    openai.py       OpenAI Batch API adapter (AsyncOpenAI, /v1/responses)

  store/            ❌ Phase 2 — not created yet
  api/              ❌ Phase 3 — not created yet
  daemon/           ❌ Phase 4 — not created yet
  cli/              ❌ Phase 3 — not created yet
```

**Tests:** `backend/tests/test_engine_smoke.py` — full pipeline (build → submit → monitor → download → merge) against a `MockProvider`. This is the conformance test for the `Provider` Protocol.

### Frontend — `frontend/src/`

Placeholder only. `App.tsx` renders a centered "batchkit" heading. No API client, no canvas, no React Flow yet. Dependencies are React + Vite + Tailwind + vitest.

### Shell — `shell/src/`

40-line Electron stub. `main.js` opens a BrowserWindow; loads `VITE_DEV_SERVER_URL` in dev or `frontend/dist/index.html` in prod. **Does not spawn Python backend yet** (Phase 7). Security defaults: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.

### Examples — `examples/`

Three reference task specs from the **old CLI framework** (`oai_batchkit.task.BatchTask`). Kept for documentation; they reference APIs not yet reimplemented in the new engine:

- `classification_responses_api/` — structured-output classification (Responses API)
- `embeddings_corpus/` — embeddings batch
- `moderations_audit/` — moderations batch

Each has `task.py` + `run.yaml`. The new canvas will serialize node graphs into a similar shape under the hood.

---

## Domain model (read this before touching engine code)

| Type | File | Meaning |
|------|------|---------|
| `Job` | `domain/job.py` | Saved user configuration: dataset path, system prompt, schema, model, provider name |
| `Run` | `domain/job.py` | One execution of a Job. Holds `batches: dict[str, BatchRecord]` and aggregate token counters |
| `BatchRecord` | `domain/batch.py` | Engine-owned mutable record for one batch. Lifecycle: `prepared → submitted → in_progress → completed \| failed \| expired \| cancelled` |
| `BatchInfo` | `domain/batch.py` | Normalized snapshot from `Provider.retrieve_batch()` |
| `BatchEvent` | `domain/batch.py` | One poll observation — what monitor yields (WebSocket payload in Phase 3) |
| `SchemaDef` | `domain/schema.py` | User output schema as JSON Schema dict (frontend sends this; engine never imports user's Pydantic) |
| `CostEstimate` | `domain/cost.py` | Pre-flight cost projection across all rows |
| `Provider` | `providers/base.py` | Protocol: `format_request_body`, `parse_result_line`, `estimate_cost`, `upload_file`, `create_batch`, `retrieve_batch`, `cancel_batch`, `download_file` |

**Key relationships:**
- One `Job` → many `Run`s (over time)
- One `Run` → many `BatchRecord`s (CSV split into batch-sized JSONL files)
- `Run.pending_batches()` / `in_flight_batches()` / `completed_batches()` / `failed_batches()` drive monitor logic

---

## Engine pipeline (how data flows)

```
CSV file
  │
  ▼ build_batch_files()          builder.py
  │  - reads CSV with pandas
  │  - splits into batches (batch_size rows, max ~199MB per file)
  │  - calls provider.format_request_body() per row
  │  - writes JSONL files
  │  - returns list[BatchRecord] (status="prepared")
  │
  ▼ submit_and_monitor()         monitor.py
  │  - sliding window: submits pending batches up to concurrency limit
  │  - respects max_queue_tokens (OpenAI 15B enqueued cap)
  │  - asyncio.gather polls all in-flight batches
  │  - yields BatchEvent on each poll cycle
  │  - mutates BatchRecord.status in place
  │
  ▼ download_completed()         downloader.py
  │  - for each completed batch: provider.download_file()
  │  - provider.parse_result_line() per JSONL row
  │  - writes per-batch CSV + error files
  │  - updates Run token counters
  │
  ▼ merge_batch_csvs()           merger.py
     - concatenates per-batch CSVs in batch_number order
     - output columns = schema.field_names
```

**OpenAI adapter specifics** (`providers/openai.py`):
- Default endpoint: `/v1/responses` with structured JSON schema output
- Also supports `/v1/chat/completions`, `/v1/embeddings`, `/v1/completions`
- AsyncOpenAI with tenacity retries (except `BadRequestError`)
- Status mapping: OpenAI statuses → our `BatchStatus` literal
- Model pricing table in `MODEL_PRICING` dict
- Raises `BillingLimitError` on `billing_hard_limit_reached`

---

## Development commands

Run from repo root. Each layer has its own README with more detail.

```bash
# Backend (from backend/)
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy src
pytest                                    # includes engine smoke test

# Frontend (from frontend/)
npm install
npm run dev                               # Vite HMR on default port
npm run lint && npm run typecheck && npm run test

# Shell (from shell/)
npm install
VITE_DEV_SERVER_URL=http://localhost:5173 npm start   # dev with HMR
npm start                                 # loads frontend/dist/ statically

# Pre-commit (Python, from repo root)
pre-commit install
```

**CI must pass:** backend (ruff + mypy + pytest), frontend (eslint + prettier + tsc + vitest), shell (eslint).

---

## Where to work for common tasks

| Task | Start here |
|------|-----------|
| Add/modify domain types | `backend/src/batchkit/domain/` — update tests first |
| Change batch building logic | `backend/src/batchkit/engine/builder.py` |
| Change submit/poll behavior | `backend/src/batchkit/engine/monitor.py` |
| Add a new LLM provider | New file in `providers/` implementing `Provider` Protocol; add MockProvider-style test |
| OpenAI wire format changes | `backend/src/batchkit/providers/openai.py` |
| SQLite persistence (Phase 2) | Create `store/models.py`, `store/repo.py`, `store/db.py` |
| REST API (Phase 3) | Create `api/app.py`, `api/routes/`, `api/ws.py` |
| Frontend canvas (Phase 6) | `frontend/src/canvas/` (doesn't exist yet) |
| Electron packaging (Phase 7) | `shell/src/main.js` — add Python subprocess spawn |

**Do not modify** `examples/` task files unless explicitly asked — they document the old CLI shape.

---

## Planned but not yet created

These directories are in the architecture plan but **do not exist in the repo yet**. Do not assume they are implemented:

- `backend/src/batchkit/store/` — SQLAlchemy models + repositories
- `backend/src/batchkit/api/` — FastAPI routes + WebSocket
- `backend/src/batchkit/daemon/` — background poller
- `backend/src/batchkit/cli/` — Typer CLI wrapper
- `frontend/src/api/`, `frontend/src/ws/`, `frontend/src/canvas/` — frontend layers

When implementing Phase 2+, follow the plan in `plans/` and keep domain/engine free of framework imports.

---

## Maintaining this file

`AGENTS.md` is living documentation. **Agents must update it as the project progresses** — not only when the user asks. This keeps Cursor, Claude Code, Codex, and cloud agents aligned without re-exploring the repo every session.

### When to update

Update in the **same session** (and include in the **same PR** as the code change, unless the user says otherwise) when you:

- Complete or start a phased milestone (Phase 0–8)
- Add, remove, or rename a module under `backend/`, `frontend/`, or `shell/`
- Change architecture decisions, domain model, or pipeline flow
- Add dev commands, dependencies, or CI jobs
- Move or add entry points in the "Where to work" table

### What to update

1. **Current build status** table
2. **What exists today (file map)**
3. **Planned but not yet created** (remove items that now exist)
4. **Where to work for common tasks**
5. **Tech stack table** (major new deps)
6. **Domain model** (new types)

### What not to update

- Behavioral rules (git, workflow, communication) unless the user asks
- Session chatter or line-level implementation detail better left in code
- Trivial bugfixes with no structural impact

### How

- Surgical edits to affected sections only
- Preserve existing structure and tone
- When unsure, update the file map and build status table at minimum

Global policy: Cursor **User Rules** (`~/.cursor/user-rules/agents-md-maintenance.md`) + skill `maintain-agents-md` apply in every project.

---

## About the developer

I'm a CS + business student and aspiring AI engineer — a **beginner programmer** using this project to learn agentic engineering, software development life cycle, Applied AI system design, and deployment end-to-end.

**Primary goal in every session:** learning, alongside shipping world-class code.

When working with me:

- **Explain the "why"** behind library, pattern, and architecture choices (2–5 sentences). Don't assume I'd make the same call.
- **Don't assume technical fluency.** Briefly explain load-bearing concepts (async, ORMs, IPC, etc.) when they matter.
- **Teach bottom-up with analogies** — concrete primitive first, abstraction second.
- **Flag what's worth reading up on** when a concept would benefit from deeper study.
- **Push back when I'm wrong.** I'm here to learn; say so and explain why.
- Keep explanations in chat prose, not in code comments. Skip trivia. Don't re-explain within a session.

---

## Agent workflow

### 1. Think before coding

- State assumptions explicitly. If uncertain, ask once, then proceed.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop and name what's confusing.

### 2. Simplicity first

- Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked.
- No abstractions for single-use code.
- No error handling for impossible scenarios.
- Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical changes

- Touch only what you must. Don't refactor unrelated code.
- Match existing style, even if you'd do it differently.
- Remove imports/variables/functions that **your** changes made unused.
- Don't remove pre-existing dead code unless asked.
- Every changed line should trace directly to the request.

### 4. Goal-driven execution

Transform tasks into verifiable goals and loop until verified:

- "Add validation" → write tests for invalid inputs, then make them pass
- "Fix the bug" → reproduce it, then fix it
- "Refactor X" → ensure tests pass before and after

For multi-step tasks, state a brief plan with verification steps.

### Code principles

1. **Minimize scope** — simplest correct diff; no unrelated changes.
2. **Avoid over-engineering** — no premature abstractions or excessive error handling.
3. **Use existing conventions** — read surrounding code first; match naming, types, and style.
4. **Comments sparingly** — only for non-obvious business logic.
5. **Useful tests only** — add tests when requested or when they cover real behavior.

### Execution environment

This is a real environment with full shell access. Run commands and investigate problems yourself. Do not give up after a single failure — diagnose and retry.

Follow all instructions in this file, tool descriptions, and skill files precisely and completely.

---

## Git commits

**Only create commits when explicitly requested.** If unclear, ask first.

Git safety:

- NEVER update git config
- NEVER run destructive git commands (`push --force`, hard reset, etc.) unless explicitly requested
- NEVER skip hooks (`--no-verify`, `--no-gpg-sign`, etc.) unless explicitly requested
- NEVER force push to main/master — warn the user if they request it
- Avoid `git commit --amend` unless ALL of: user requested amend, HEAD commit was created by you this session, commit has NOT been pushed
- If commit FAILED or was REJECTED by hook, NEVER amend — fix and create a NEW commit
- NEVER commit files likely containing secrets (`.env`, credentials, keys)
- Do not create empty commits

When asked to commit:

1. Run `git status`, `git diff`, and `git log` to understand state and message style
2. Stage relevant files, commit with a 1–2 sentence message focused on **why**
3. Verify with `git status` after commit
4. Do NOT push unless explicitly asked
5. Never use interactive git flags (`-i`)

Pass commit messages via HEREDOC for correct formatting.

---

## Pull requests

Use the `gh` CLI for GitHub tasks (issues, PRs, checks, releases).

When asked to create a PR:

1. Run `git status`, `git diff`, check remote tracking, and `git log` + `git diff [base]...HEAD`
2. Review ALL commits that will be included, not just the latest
3. Push with `-u` if needed, then `gh pr create` with Summary and Test plan sections
4. Return the PR URL
5. Do NOT update git config

---

## Communication

- Use code citation blocks (`startLine:endLine:filepath`) when referencing existing code — not inline backtick chains.
- Citation fences must be on their own line, never prefixed by list markers.
- Write full commands in suggested shell blocks — no `...` omissions.
- Use markdown links for URLs and file paths.
- Write like a technical blog post: precise, structured, complete sentences.
- Keep responses proportional to task complexity.
- Do not overuse bolding or backticks for decoration.
- Avoid engagement bait at the end of responses.

---

## Engineering conventions (this repo)

### Python (`backend/`)

- `ruff` + `mypy --strict`, `pytest` + `pytest-asyncio`
- Pydantic for every DTO crossing a boundary (Phase 3 API layer)
- SQLAlchemy 2.0 async (no Alembic in MVP — `create_all()` at startup)
- Domain types and tests first, then adapters
- Line length 100, double quotes (ruff config in `pyproject.toml`)

### Frontend (`frontend/`)

- TypeScript strict, eslint + prettier, vitest
- Hand-write TypeScript types mirroring FastAPI models (codegen post-MVP)
- React Query for server state; separate WebSocket hook for live events

### CI

- GitHub Actions: lint + typecheck + tests on every PR (`.github/workflows/ci.yml`)
- Pre-commit hooks for Python

### Secrets

- Never commit `.env`, keys, or credentials
- Provider credentials will use macOS Keychain (Phase 7), not env vars in production
- `.cursorignore` excludes secrets from indexing

---

## What not to do unless asked

- Create commits or PRs
- Add features beyond the request
- Refactor unrelated code
- Add markdown files the user didn't ask for
- Add tests that trivially assert the obvious
- Assume Phase 2+ code exists when it doesn't (check the file map above)
