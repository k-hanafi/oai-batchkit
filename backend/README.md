# batchkit (backend)

FastAPI + SQLAlchemy backend for the batchkit desktop app. Hosts the ports-and-adapters job engine, provider adapters (OpenAI today), persistence layer, REST + WebSocket API, and the background poller daemon.

## Local setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Common commands

```bash
ruff check .          # lint
ruff format .         # format
mypy src              # typecheck
pytest                # tests
```
