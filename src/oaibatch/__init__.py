"""oaibatch: a generalizable framework for the OpenAI Batch API.

Public re-exports keep one stable import surface for users:

    from oaibatch import BatchTask, Run, Endpoint, BatchRecord, CostEstimate

Everything else is implementation detail.
"""

from __future__ import annotations

from oaibatch.api import Run
from oaibatch.core.state import BatchRecord, BatchStatus, PipelineState
from oaibatch.core.tokens import CostEstimate
from oaibatch.task import BatchTask, Endpoint, InputSource, Row

__version__ = "0.0.1"

__all__ = [
    "BatchRecord",
    "BatchStatus",
    "BatchTask",
    "CostEstimate",
    "Endpoint",
    "InputSource",
    "PipelineState",
    "Row",
    "Run",
    "__version__",
]
