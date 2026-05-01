"""SMTP email notifier.

Uses `smtplib` from the stdlib so it has no extra dependencies. Configured
via env vars (OAIBATCH_SMTP_HOST, OAIBATCH_SMTP_PORT, OAIBATCH_SMTP_USER,
OAIBATCH_SMTP_PASSWORD) or constructor args.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaibatch.api import Run


class EmailNotifier:
    """Sends a multipart email with the cost report attached as text.

    Subject line includes the run name and a status emoji (so users
    triaging a flooded inbox can scan quickly). The body mirrors the Slack
    message format for consistency.
    """

    smtp_host: str
    smtp_port: int
    sender: str
    recipients: list[str]

    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        sender: str,
        recipients: list[str],
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients
        self._username = username
        self._password = password

    def on_run_completed(self, run: Run) -> None:
        raise NotImplementedError

    def on_run_failed(self, run: Run, error: BaseException) -> None:
        raise NotImplementedError
