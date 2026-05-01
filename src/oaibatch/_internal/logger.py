"""Structured logging: Rich console + per-run rotating file handler.

Console output uses Rich for human-readable formatting; file output uses
plain text so it's grep-friendly when the run dir is shipped or archived.

The `setup_logging` function is idempotent: calling it twice in one process
does not double-attach handlers. This matters because the CLI may invoke
multiple `Run` methods in one process (e.g. `oaibatch run` calls prepare
then submit then download then merge).
"""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(
    run_dir: Path | None = None,
    *,
    level: int = logging.INFO,
    rich_console: bool = True,
) -> None:
    """Configure the root logger with console + optional file handlers.

    Args:
        run_dir: If provided, attach a `RotatingFileHandler` writing to
            `<run_dir>/run.log`. Required for `submit` / `monitor` /
            `download` so audit trails are preserved.
        level: Logging level for both handlers.
        rich_console: When True (default), use `rich.logging.RichHandler`
            for the console; when False, fall back to a plain
            `StreamHandler` (for headless / CI environments).

    Idempotent: subsequent calls with the same `run_dir` are no-ops.
    """
    raise NotImplementedError
