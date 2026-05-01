"""The Notifier Protocol.

Concrete notifiers (Slack, email, desktop, custom user hooks) implement this
contract. The framework calls the appropriate hook from `Run.submit` and
`Run.run` at terminal events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from oaibatch.api import Run


@runtime_checkable
class Notifier(Protocol):
    """Pluggable completion / failure notifier.

    Implementations should be cheap to call and tolerant of network failures
    (a notifier crash must not propagate up and break the run that just
    completed). The framework wraps notifier calls in try/except and logs
    failures.
    """

    def on_run_completed(self, run: Run) -> None:
        """Called when every batch in `run` reaches a terminal state.

        Receives the final `Run` so the notifier can read totals, cost, or
        cache stats off `run.state` if it wants to include them in the
        message body.
        """
        ...

    def on_run_failed(self, run: Run, error: BaseException) -> None:
        """Called when the submit/monitor loop aborts before completion.

        The `error` is the original exception (typically a `BillingLimitError`
        or a connectivity problem). Use it for the message body so users can
        tell why the run stopped.
        """
        ...
