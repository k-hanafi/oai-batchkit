"""Slack incoming-webhook notifier.

Only depends on `requests` (declared in the `notify` extras). Wire up via:

    pip install 'oaibatch[notify]'

    notifier = SlackNotifier(webhook_url=os.environ["OAIBATCH_SLACK_WEBHOOK"])
    run.submit(notifiers=[notifier])
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaibatch.api import Run


class SlackNotifier:
    """Posts a one-line summary to a Slack incoming webhook.

    The summary includes the run name, model, total rows, cache hit rate,
    and total cost so the message is self-contained for someone glancing
    at their phone.
    """

    webhook_url: str
    channel: str | None

    def __init__(self, webhook_url: str, *, channel: str | None = None) -> None:
        self.webhook_url = webhook_url
        self.channel = channel

    def on_run_completed(self, run: Run) -> None:
        raise NotImplementedError

    def on_run_failed(self, run: Run, error: BaseException) -> None:
        raise NotImplementedError
