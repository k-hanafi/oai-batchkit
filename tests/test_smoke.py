"""Smoke tests proving the package imports and the CLI surface is registered.

These tests run without touching the network or the filesystem (except via
typer's test runner). They guard against the "scaffolding regressed and
nothing imports anymore" failure mode.
"""

from __future__ import annotations

from typer.testing import CliRunner

import oaibatch
from oaibatch.cli import app


def test_package_exports_public_api() -> None:
    """The advertised top-level imports must all resolve."""
    assert hasattr(oaibatch, "__version__")
    assert hasattr(oaibatch, "BatchTask")
    assert hasattr(oaibatch, "Endpoint")
    assert hasattr(oaibatch, "Run")
    assert hasattr(oaibatch, "BatchRecord")
    assert hasattr(oaibatch, "PipelineState")
    assert hasattr(oaibatch, "CostEstimate")


def test_cli_help_lists_all_tier_one_commands() -> None:
    """`oaibatch --help` must enumerate every Tier 1 lifecycle command."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.stdout
    for command in (
        "new",
        "prepare",
        "submit",
        "status",
        "download",
        "retry",
        "merge",
        "run",
        "test",
    ):
        assert command in result.stdout, f"Tier 1 command '{command}' missing from --help"


def test_cli_help_lists_tier_two_commands() -> None:
    """Observability + safety commands must be visible."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.stdout
    for command in (
        "list",
        "inspect",
        "validate",
        "cancel",
        "cleanup",
        "logs",
        "estimate",
        "cost",
        "cache-report",
    ):
        assert command in result.stdout, f"Tier 2 command '{command}' missing from --help"


def test_version_command_prints_package_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert oaibatch.__version__ in result.stdout


def test_pricing_json_is_packaged_and_well_formed() -> None:
    """The packaged `pricing.json` must be readable and contain the expected keys."""
    import json
    from importlib import resources

    raw = resources.files("oaibatch").joinpath("pricing.json").read_text()
    data = json.loads(raw)
    assert "discounts" in data
    assert "models" in data
    assert "batch" in data["discounts"]
    assert "cache" in data["discounts"]
    assert isinstance(data["models"], dict)
    assert len(data["models"]) > 0
