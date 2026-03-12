from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    import typer
    from activewatcher_autotag import cli

    _HAS_TYPER = True
except Exception:  # pragma: no cover - dependency guard
    typer = None  # type: ignore[assignment]
    cli = None  # type: ignore[assignment]
    _HAS_TYPER = False


@contextmanager
def _dummy_lock(*args, **kwargs):
    yield Path("/tmp/activewatcher-test.lock")


@unittest.skipUnless(_HAS_TYPER, "typer dependency is not installed")
class CliErrorMappingTests(unittest.TestCase):
    def test_scan_maps_existing_run_to_bad_parameter(self) -> None:
        with (
            patch("activewatcher_autotag.cli.run_lock", new=_dummy_lock),
            patch(
                "activewatcher_autotag.cli.create_run",
                side_effect=FileExistsError("already exists"),
            ),
        ):
            with self.assertRaises(typer.BadParameter) as ctx:
                cli.scan(from_spec=None, to_spec=None, run_id="run_existing")

        self.assertIn("run already exists", str(ctx.exception))

    def test_suggest_maps_missing_run_to_bad_parameter(self) -> None:
        with (
            patch("activewatcher_autotag.cli.run_lock", new=_dummy_lock),
            patch(
                "activewatcher_autotag.cli.resolve_run_root",
                side_effect=FileNotFoundError("run not found: missing"),
            ),
        ):
            with self.assertRaises(typer.BadParameter) as ctx:
                cli.suggest(run_id="missing")

        self.assertIn("run not found", str(ctx.exception))

    def test_evaluate_maps_missing_run_to_bad_parameter(self) -> None:
        with (
            patch("activewatcher_autotag.cli.run_lock", new=_dummy_lock),
            patch(
                "activewatcher_autotag.cli.resolve_run_root",
                side_effect=FileNotFoundError("run not found: missing"),
            ),
        ):
            with self.assertRaises(typer.BadParameter) as ctx:
                cli.evaluate(run_id="missing")

        self.assertIn("run not found", str(ctx.exception))

    def test_apply_maps_missing_run_to_bad_parameter(self) -> None:
        with (
            patch("activewatcher_autotag.cli.run_lock", new=_dummy_lock),
            patch(
                "activewatcher_autotag.cli.resolve_run_root",
                side_effect=FileNotFoundError("run not found: missing"),
            ),
        ):
            with self.assertRaises(typer.BadParameter) as ctx:
                cli.apply(run_id="missing", confirm="APPLY")

        self.assertIn("run not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
