"""Per-run advisory lock to prevent concurrent CLI invocations from colliding.

Two `oaibatch submit --run X` calls running simultaneously would double-
upload files and corrupt `state.json`. The lockfile makes the second
invocation refuse with a clear error pointing at the holder PID.

Implementation contract: use `fcntl.flock` (POSIX) for exclusivity, write
the holder PID + start timestamp into the lockfile body so error messages
can identify the offender.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType


class RunLockError(RuntimeError):
    """Another oaibatch process holds the run's lock.

    The error message includes the holder PID and acquisition time so the
    user can decide whether to wait, kill, or override.
    """


class RunLock(AbstractContextManager["RunLock"]):
    """Advisory lock for one run directory.

    Usage:

        with RunLock(run_dir):
            # exclusive section
            ...

    Raises `RunLockError` immediately if the lock is held by another
    process; does not block. The CLI surfaces this as a non-zero exit
    so users can script around it.
    """

    run_dir: Path
    path: Path

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.path = run_dir / "lockfile"

    def __enter__(self) -> RunLock:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError
