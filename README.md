# oai-batchkit

A visual desktop app for running massive OpenAI [Batch API](https://platform.openai.com/docs/guides/batch) jobs without rebuilding the surrounding pipeline every time.

> **Status:** under active rebuild. The original Python CLI framework is being replaced with an Electron + React + FastAPI desktop app so the toolkit is approachable to non-engineer researchers. Phase 0 (monorepo scaffold) is done. Full architecture and reasoning in [`.cursor/plans/batchkit-mvp-architecture_4b392a9e.plan.md`](.cursor/plans/batchkit-mvp-architecture_4b392a9e.plan.md).

## Table of contents

- [Why this exists](#why-this-exists)
- [What it handles](#what-it-handles)
- [Roadmap](#roadmap)
- [Repository structure](#repository-structure)
- [Setup](#setup)
- [Development](#development)
- [Related work](#related-work)
- [License](#license)

## Why this exists

The Batch API is the cheapest, highest-throughput way to run large LLM jobs, but every research team that uses it ends up reinventing the same pipeline: cost estimation, JSONL building, retry-aware submission, queue-pressure-aware monitoring, failure recovery, and result merging. Synchronous APIs are not a substitute when a project crosses millions or billions of tokens.

I built that pipeline three times across two research projects before pulling it into one library. The biggest: classifying roughly 280,000 startups into a research-grade taxonomy of 10 AI-native categories. At that scale, the engineering around the model is the entire job. I contributed back to OpenAI's Batch API documentation during a developer interview with the API product team.

## What it handles

- **Dataset-to-batch preparation.** CSV and structured tables become valid Batch API jobs.
- **Structured outputs.** Pydantic schemas turn model responses into typed rows.
- **Cost awareness.** Pre-flight estimates and post-run cost tracking.
- **Rate-limit and queue management.** Stays under the 15B-token enqueued cap without manual babysitting.
- **Failure recovery.** Failed and expired rows get retried without restarting the run.
- **State tracking.** Long-running jobs are resumable and auditable.
- **Final dataset assembly.** Successful results merged into one clean output table.

## Roadmap

Eight phases, each ending with a runnable artifact.

- [x] **Phase 0:** Monorepo scaffold (backend, frontend, shell) with strict typing, linting, and CI from day 1.
- [ ] **Phase 1:** Port the batch engine behind a `Provider` protocol (OpenAI today, Anthropic and Google later as new files, not refactors).
- [ ] **Phase 2:** SQLite-backed job state via SQLAlchemy.
- [ ] **Phase 3:** FastAPI REST API plus a WebSocket channel for live progress.
- [ ] **Phase 4:** Background poller so jobs survive window close.
- [ ] **Phase 5:** React + TypeScript frontend foundation.
- [ ] **Phase 6:** React Flow canvas with dataset, prompt, model, and output nodes.
- [ ] **Phase 7:** Electron shell with macOS code signing and notarization.
- [ ] **Phase 8:** First DMG release.

## Repository structure

```
oai-batchkit/
  backend/    FastAPI app, batch engine, SQLite store, OpenAI provider adapter
  frontend/   Vite + React + TypeScript + Tailwind. The visual canvas lives here.
  shell/      Electron shell. Hosts the frontend and (later) supervises the backend.
  examples/   Reference task specifications kept across the rebuild.
```

Each subdirectory has its own `README.md` with the commands specific to that layer:

- [`backend/README.md`](backend/README.md)
- [`frontend/README.md`](frontend/README.md)
- [`shell/README.md`](shell/README.md)

## Setup

### Prerequisites

- Python 3.11+
- Node 20+
- macOS for now (other platforms are post-MVP)

### Install

```bash
git clone https://github.com/k-hanafi/oai-batchkit.git
cd oai-batchkit

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ..

# Frontend
cd frontend && npm install && cd ..

# Shell
cd shell && npm install && cd ..
```

## Development

Each layer is independent. The most common commands:

```bash
# Backend
cd backend
ruff check . && ruff format --check .
mypy src
pytest

# Frontend
cd frontend
npm run dev            # Vite dev server with HMR
npm run lint
npm run typecheck
npm run test

# Shell
cd shell
npm start              # launch dev Electron window
npm run lint
```

Pre-commit hooks (Python only for now):

```bash
pre-commit install
```

CI runs lint, typecheck, and tests for all three layers on every PR. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Related work

`oai-batchkit` was extracted from two research repos that needed the same pipeline:

- [ai-native-startup-classification](https://github.com/k-hanafi/ai-native-startup-classification): the 280k-startup taxonomy project.
- [llm_directness_experiment](https://github.com/k-hanafi/llm_directness_experiment): LLMs studying language and communication patterns.

## License

MIT. See [LICENSE](LICENSE).
