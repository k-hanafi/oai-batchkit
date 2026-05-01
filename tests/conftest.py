"""Pytest configuration shared across the test suite.

Kept minimal at scaffolding time. As implementation phases land, this file
will hold:
  - fixtures for an in-memory PipelineState
  - fixtures for a stubbed OpenAI client (no network)
  - a tmp_path-based fixture that materializes a fully-formed run dir
"""

from __future__ import annotations
