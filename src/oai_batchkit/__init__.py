"""oai-batchkit: a generalizable framework for the OpenAI Batch API.

Public re-exports keep one stable import surface for users:

    from oai_batchkit import BatchTask, Run, Endpoint, BatchRecord, CostEstimate

Everything else is implementation detail.
"""

from __future__ import annotations

from oai_batchkit.api import Run
from oai_batchkit.core.state import BatchRecord, BatchStatus, PipelineState
from oai_batchkit.core.tokens import CostEstimate
from oai_batchkit.task import BatchTask, Endpoint, InputSource, Row

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
