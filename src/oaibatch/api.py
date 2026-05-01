"""Public Python API: the `Run` class.

A Run is one `(task, params)` cell with its own `run_dir`. Every CLI verb
(`prepare`, `submit`, `status`, `download`, `retry`, `merge`, ...) is a
method on `Run`, so the CLI is a thin Typer wrapper and a future GUI gets
the same surface for free.

Run directory layout (canonical):

    <run_dir>/
    ├── run.yaml         # immutable: task name, params, model, batch_size,
    │                    # dataset fingerprint, prompt fingerprint
    ├── state.json       # checkpoint, atomic write
    ├── run.log          # rotating
    ├── lockfile         # per-run flock for concurrent-CLI safety
    ├── requests/        # batch_NNNN.jsonl
    ├── results/         # batch_NNNN.jsonl (raw)
    ├── errors/          # batch_NNNN_errors.jsonl
    ├── outputs/         # batch_NNNN.csv (parsed + validated, per-task shape)
    └── final.csv        # merged output across all batches
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from oaibatch.core.state import PipelineState
from oaibatch.core.tokens import CostEstimate
from oaibatch.task import BatchTask, InputSource


class Run:
    """One concrete execution of a `BatchTask` with frozen params.

    Construct via `Run.create(...)` for a fresh run or `Run.load(run_dir)`
    to resume an existing one. The class is intentionally not a dataclass:
    it owns side-effecting operations (file IO, network calls), and its
    state lives in `self.state` (a `PipelineState`).
    """

    task: BatchTask
    name: str
    params: Mapping[str, Any]
    run_dir: Path
    state: PipelineState

    def __init__(
        self,
        task: BatchTask,
        name: str,
        params: Mapping[str, Any],
        run_dir: Path,
        state: PipelineState,
    ) -> None:
        self.task = task
        self.name = name
        self.params = params
        self.run_dir = run_dir
        self.state = state

    @classmethod
    def create(
        cls,
        task: BatchTask,
        name: str,
        params: Mapping[str, Any],
        run_dir: Path,
    ) -> Run:
        """Bootstrap a new run directory, write `run.yaml`, return the Run.

        Raises if `run_dir` already exists and is non-empty.
        """
        raise NotImplementedError

    @classmethod
    def load(cls, run_dir: Path) -> Run:
        """Resume an existing run from `run_dir`. Reads `run.yaml` + `state.json`.

        Imports the task module declared in `run.yaml` so the user's
        `BatchTask` implementation is rebound to this Run.
        """
        raise NotImplementedError

    # -- Lifecycle methods (CLI verbs map 1:1 onto these) ---------------------

    def prepare(
        self,
        source: InputSource,
        *,
        model: str,
        batch_size: int,
        dry_run: bool = False,
    ) -> CostEstimate:
        """Build per-batch JSONL request files; return the pre-flight cost estimate.

        If `dry_run=True`, computes and returns the estimate without writing
        any files. Otherwise writes `<run_dir>/requests/batch_NNNN.jsonl` and
        registers each batch in `self.state`.
        """
        raise NotImplementedError

    def submit(self, *, concurrency: int = 1) -> None:
        """Upload prepared JSONL files and create batch jobs with sliding-window
        queue pressure control. Polls until all batches reach a terminal state.

        Resumable: on Ctrl-C or crash, re-invoking picks up where it left off
        because `state.json` is written atomically after each step.
        """
        raise NotImplementedError

    def status(self, *, watch: bool = False) -> None:
        """Print a Rich status table. With `watch=True`, refresh until all
        batches are terminal."""
        raise NotImplementedError

    def download(self) -> None:
        """Fetch result + error files for every completed batch and write
        per-batch CSVs by routing each row through `task.parse_result`."""
        raise NotImplementedError

    def retry(self) -> None:
        """Collect failed `custom_id`s from error files and rebuild new
        batch JSONLs containing only those requests. Registers the new
        batches in `self.state` for the next `submit`."""
        raise NotImplementedError

    def merge(self, out: Path | None = None) -> Path:
        """Concatenate per-batch CSVs into a single `final.csv` (or `out`).
        Prints distribution + cost report. Returns the output path."""
        raise NotImplementedError

    def cancel(self, *, batch: int | None = None, all_in_flight: bool = False) -> None:
        """Cancel one or all in-flight batches via `client.batches.cancel`."""
        raise NotImplementedError

    def cleanup(self) -> None:
        """Delete uploaded `file_id`s from OpenAI once results are downloaded.
        Refuses if any batch is still in-flight."""
        raise NotImplementedError

    def inspect(self, custom_id: str) -> dict[str, Any]:
        """Return the request body, raw response, parsed output, validation
        status, and cost-of-this-row for one custom_id. Used by
        `oaibatch inspect`."""
        raise NotImplementedError


class RunRegistry:
    """Discover all runs under a project root.

    Used by `oaibatch list` to produce the global status table.
    """

    @staticmethod
    def discover(project_root: Path) -> list[Path]:
        """Return every run_dir found under `project_root/runs/**`."""
        raise NotImplementedError
