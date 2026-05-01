"""Stable hashing for prompt + dataset drift detection.

Stored on `PipelineState.prompt_fingerprint` and `PipelineState.dataset_fingerprint`
at run-creation time. Subsequent CLI verbs verify the live values match
these stored values and refuse to proceed on mismatch (with a `--force`
escape hatch).

This catches the silent-corruption case where someone edits the prompt
mid-run and the cache routing becomes incoherent without any visible
error.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def hash_text(text: str) -> str:
    """Stable hex-digest fingerprint for a prompt body or any short text.

    Implementation: SHA-256 of the UTF-8 encoded text, returned as a
    lowercase hex digest. Stable across Python versions and machines.
    """
    raise NotImplementedError


def hash_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Stream-hash a file (e.g. an input CSV or JSONL) without loading it
    into memory. Used for dataset drift detection on multi-GB inputs."""
    raise NotImplementedError


def hash_rows(rows: Iterable[object]) -> str:
    """Hash an iterable of canonicalized rows.

    Used when the input source is not file-backed (e.g. a SQL query or an
    in-memory iterable). Each row is serialized via deterministic JSON
    before being fed into the hash, so dict key ordering does not affect
    the digest.
    """
    raise NotImplementedError
