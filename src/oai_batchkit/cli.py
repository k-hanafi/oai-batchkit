"""Typer-based CLI for oai-batchkit.

Every subcommand is registered here so `oai-batchkit --help` is the public
specification of the framework's surface area. Command bodies are stubs
(`raise NotImplementedError`) at scaffolding time; subsequent
implementation phases fill them in.

Tier ordering:
  - Tier 1 (core lifecycle): new, prepare, submit, status, download,
    retry, merge, run, test
  - Tier 2 (observability + safety): list, inspect, validate, cancel,
    cleanup, logs, estimate, cost, cache-report
  - Tier 3 (differentiators, registered hidden): matrix, diff, notify,
    daemon, webhook

Hidden commands still appear under `--help all` and behave normally; they
are flagged hidden only to keep the default help output focused on Tier 1
during the early-stage period when Tier 3 is incomplete.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

app = typer.Typer(
    name="oai-batchkit",
    help=(
        "A generalizable CLI for OpenAI's Batch API. Take any structured-output "
        "task from CSV to merged results without rewriting infrastructure."
    ),
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# ---------------------------------------------------------------------------
# Tier 1 - Core lifecycle
# ---------------------------------------------------------------------------


@app.command()
def new(
    task: Annotated[str, typer.Argument(help="Task module path, e.g. 'mypkg.task:MyTask'")],
    run: Annotated[str, typer.Option(help="Run name; becomes the run-dir leaf.")],
    params: Annotated[
        Optional[list[str]],
        typer.Option("--params", "-p", help="Run params as k=v (repeatable)."),
    ] = None,
    run_dir: Annotated[
        Optional[Path],
        typer.Option(help="Where to create the run dir. Defaults to ./runs/<task>/<run>."),
    ] = None,
) -> None:
    """Bootstrap a new run directory: writes [cyan]run.yaml[/] and an empty [cyan]state.json[/]."""
    raise NotImplementedError


@app.command()
def prepare(
    run: Annotated[str, typer.Option(help="Run name (resolves to ./runs/<task>/<run>).")],
    data: Annotated[
        Optional[Path],
        typer.Option(help="Input CSV / JSONL path. Overrides the run.yaml default."),
    ] = None,
    rows: Annotated[
        Optional[str],
        typer.Option(help="Row range to process, e.g. '0:50000'."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print cost breakdown only. No files written."),
    ] = False,
) -> None:
    """Build per-batch JSONL request files; print pre-flight cost estimate."""
    raise NotImplementedError


@app.command()
def submit(
    run: Annotated[str, typer.Option(help="Run name.")],
    concurrency: Annotated[
        int,
        typer.Option(help="Max batches in-flight simultaneously (sliding window)."),
    ] = 1,
) -> None:
    """Upload prepared JSONLs and create batch jobs; monitor until terminal."""
    raise NotImplementedError


@app.command()
def status(
    run: Annotated[str, typer.Option(help="Run name.")],
    watch: Annotated[
        bool,
        typer.Option("--watch", help="Refresh until all batches reach a terminal state."),
    ] = False,
) -> None:
    """Print a Rich status table for one run."""
    raise NotImplementedError


@app.command()
def download(
    run: Annotated[str, typer.Option(help="Run name.")],
) -> None:
    """Fetch result + error files for every completed batch and parse to per-batch CSVs."""
    raise NotImplementedError


@app.command()
def retry(
    run: Annotated[str, typer.Option(help="Run name.")],
) -> None:
    """Rebuild JSONLs for failed / expired requests and register new batches."""
    raise NotImplementedError


@app.command()
def merge(
    run: Annotated[str, typer.Option(help="Run name.")],
    out: Annotated[
        Optional[Path],
        typer.Option(help="Output CSV path. Defaults to <run_dir>/final.csv."),
    ] = None,
) -> None:
    """Concatenate per-batch CSVs into one final CSV; print distribution + cost report."""
    raise NotImplementedError


@app.command(name="run")
def run_cmd(
    run: Annotated[str, typer.Option(help="Run name.")],
    data: Annotated[Optional[Path], typer.Option(help="Input CSV / JSONL path.")] = None,
    rows: Annotated[Optional[str], typer.Option(help="Row range, e.g. '0:50000'.")] = None,
    concurrency: Annotated[int, typer.Option(help="Sliding-window concurrency.")] = 1,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Stop after the prepare cost-estimate."),
    ] = False,
    out: Annotated[Optional[Path], typer.Option(help="Final merged CSV path.")] = None,
) -> None:
    """Full pipeline: prepare -> submit -> download -> merge."""
    raise NotImplementedError


@app.command()
def test(
    run: Annotated[str, typer.Option(help="Run name.")],
    row: Annotated[
        str,
        typer.Option(help="Row identifier (matched against the task's custom_id source field)."),
    ],
) -> None:
    """Classify one row synchronously via the [cyan]flex[/] tier for cheap prompt iteration."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tier 2 - Observability + safety
# ---------------------------------------------------------------------------


@app.command(name="list")
def list_runs(
    project_root: Annotated[
        Optional[Path],
        typer.Option(help="Project root to scan. Defaults to cwd."),
    ] = None,
    all_projects: Annotated[
        bool,
        typer.Option("--all-projects", help="Scan every project under ~/.oai-batchkit/projects/."),
    ] = False,
) -> None:
    """List every run with status badges, cost so far, and last-activity time."""
    raise NotImplementedError


@app.command()
def inspect(
    run: Annotated[str, typer.Option(help="Run name.")],
    custom_id: Annotated[str, typer.Option(help="The custom_id of the row to inspect.")],
) -> None:
    """Show request, raw response, parsed output, validation status, and cost for one row."""
    raise NotImplementedError


@app.command()
def validate(
    jsonl: Annotated[Path, typer.Argument(help="Path to a Batch API JSONL request file.")],
) -> None:
    """Lint a JSONL file: file size, body shape, custom_id uniqueness, model accessibility."""
    raise NotImplementedError


@app.command()
def cancel(
    run: Annotated[str, typer.Option(help="Run name.")],
    batch: Annotated[Optional[int], typer.Option(help="Cancel a specific batch number only.")] = None,
    all_in_flight: Annotated[
        bool,
        typer.Option("--all", help="Cancel every in-flight batch in the run."),
    ] = False,
) -> None:
    """Cancel one or all in-flight batches via [cyan]client.batches.cancel[/]."""
    raise NotImplementedError


@app.command()
def cleanup(
    run: Annotated[str, typer.Option(help="Run name.")],
) -> None:
    """Delete uploaded file_ids from OpenAI once results are downloaded."""
    raise NotImplementedError


@app.command()
def logs(
    run: Annotated[str, typer.Option(help="Run name.")],
    tail: Annotated[Optional[int], typer.Option(help="Show only the last N lines.")] = None,
    grep: Annotated[Optional[str], typer.Option(help="Filter lines matching this regex.")] = None,
) -> None:
    """Print [cyan]<run_dir>/run.log[/] with tail + grep filtering."""
    raise NotImplementedError


@app.command()
def estimate(
    jsonl: Annotated[Path, typer.Argument(help="Path to a Batch API JSONL request file.")],
) -> None:
    """Pre-flight cost estimate for any pre-built JSONL file."""
    raise NotImplementedError


@app.command()
def cost(
    run: Annotated[str, typer.Option(help="Run name.")],
) -> None:
    """Print the run's measured cost breakdown and predicted-vs-actual drift."""
    raise NotImplementedError


@app.command(name="cache-report")
def cache_report(
    run: Annotated[str, typer.Option(help="Run name.")],
) -> None:
    """Per-batch prompt-cache hit rate; flags batches that diverge from the run mean."""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tier 3 - Differentiators (registered, hidden until implementation lands)
# ---------------------------------------------------------------------------


@app.command(hidden=True)
def matrix(
    task: Annotated[str, typer.Argument(help="Task module path.")],
    grid: Annotated[
        list[str],
        typer.Option("--grid", help="Param grid, e.g. 'model=gpt-5-nano,gpt-5-mini' (repeatable)."),
    ],
) -> None:
    """Fan a task across a parameter grid; one run dir per cell. [dim](planned, not yet implemented)[/]"""
    raise NotImplementedError


@app.command(hidden=True)
def diff(
    run_a: Annotated[str, typer.Option("--run-a", help="First run name.")],
    run_b: Annotated[str, typer.Option("--run-b", help="Second run name.")],
    axis: Annotated[
        Optional[str],
        typer.Option(help="Schema field to compare on (e.g. 'subclass')."),
    ] = None,
) -> None:
    """Paired-row comparison: kappa, McNemar, confusion matrix. [dim](planned)[/]"""
    raise NotImplementedError


@app.command(hidden=True)
def notify(
    run: Annotated[str, typer.Option(help="Run name.")],
    on: Annotated[str, typer.Option(help="Event: 'completion' | 'failure'.")],
    to: Annotated[str, typer.Option(help="Notifier target, e.g. 'slack:#research'.")],
) -> None:
    """Register a notifier on a run. [dim](planned)[/]"""
    raise NotImplementedError


@app.command(hidden=True)
def daemon(
    action: Annotated[str, typer.Argument(help="'start' | 'stop' | 'status'.")],
) -> None:
    """Background process polling all runs and pushing notifications. [dim](planned)[/]"""
    raise NotImplementedError


@app.command(hidden=True)
def webhook(
    action: Annotated[str, typer.Argument(help="'serve'.")],
    port: Annotated[int, typer.Option(help="Port to listen on.")] = 8765,
) -> None:
    """Receive [cyan]batch.completed[/] webhooks from OpenAI in real time. [dim](planned)[/]"""
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


@app.command()
def version() -> None:
    """Print the oai-batchkit version and exit."""
    from oai_batchkit import __version__

    typer.echo(__version__)


def main() -> None:
    """Console-script entry point (referenced from [project.scripts] in pyproject.toml)."""
    app()


if __name__ == "__main__":
    main()
