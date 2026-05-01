"""macOS-native desktop notifier via osascript.

No third-party deps. On non-macOS systems the notifier is a no-op (and logs
a warning) so cross-platform users can leave it registered without breakage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaibatch.api import Run


class DesktopNotifier:
    """Posts a macOS notification banner via `osascript`.

    Use this when running long batches on your own machine; it's the
    fastest "ping me when done" path because it has no external auth.
    """

    sound: str | None

    def __init__(self, *, sound: str | None = "Submarine") -> None:
        self.sound = sound

    def on_run_completed(self, run: Run) -> None:
        raise NotImplementedError

    def on_run_failed(self, run: Run, error: BaseException) -> None:
        raise NotImplementedError
