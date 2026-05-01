"""Pluggable completion notifiers.

A 24-hour batch job is the perfect "ping me when done" candidate. Notifiers
let users register Slack / email / desktop hooks for run completion or
failure, so they can fire-and-forget instead of babysitting the monitor
loop.

The `Notifier` Protocol is intentionally narrow: only `on_run_completed`
and `on_run_failed`. That's enough for the common case and easy to extend
without breaking existing notifiers.
"""

from __future__ import annotations

from oaibatch.notify.base import Notifier

__all__ = ["Notifier"]
