from __future__ import annotations

# pyright: reportMissingImports=false

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "src" / "sim_ard_gaw" / "compat_scripts"
FIXTURES = ROOT / "tests" / "fixtures" / "campaigns"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(SCRIPTS))

import run_one  # noqa: E402
from test_suite.core.models import AttemptContext, AttemptStatus, TestCase  # noqa: E402
from test_suite.plugins.wind_matrix.manifest import WindMatrixManifest  # noqa: E402
from test_suite.plugins.wind_matrix.plugin import _record_from_legacy  # noqa: E402


class Phase5WrapperManifestFlowTests(unittest.TestCase):
    def test_legacy_wrapper_reads_fixture_manifest_after_phase5_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            campaign_root = Path(temp_dir)
            attempt_dir = (
                campaign_root
                / "wind_x_00_y_00"
                / "runs"
                / "attempt_001"
            )
            attempt_dir.mkdir(parents=True)
            fixture = json.loads(
                (FIXTURES / "legacy_manifest_success.json").read_text(encoding="utf-8")
            )
            fixture["campaign_root"] = str(campaign_root)
            fixture["attempts"][0]["attempt_dir"] = str(attempt_dir)
            run_one.save_manifest(campaign_root, fixture)

            manifest = WindMatrixManifest(campaign_root)
            case = TestCase(
                suite_name="wind_matrix",
                case_id="wind_x_00_y_00",
                acceptance_target_runs=1,
            )
            self.assertEqual(1, manifest.accepted_count(case))
            self.assertEqual(2, manifest.next_attempt_index(case))
            saved = manifest.load()
            self.assertEqual("success_full", saved["attempts"][0]["status"])
            self.assertEqual("success", saved["attempts"][0]["terminal_status"])

    def test_suite_cli_help_remains_available(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(SCRIPTS)])
        output = subprocess.check_output(
            [sys.executable, "-m", "test_suite.cli.run_suite", "--help"],
            text=True,
            env=env,
        )
        self.assertIn("--campaign-root", output)
        self.assertIn("--wind-world-mode", output)

    def test_wrapper_marks_legacy_analysis_failures_as_failed(self) -> None:
        case = TestCase(
            suite_name="wind_matrix",
            case_id="wind_x_00_y_00",
            parameters={"wind_x_mps": 0, "wind_y_mps": 0},
        )
        ctx = AttemptContext(
            case=case,
            campaign_root=Path("/tmp/phase5"),
            attempt_dir=Path("/tmp/phase5/wind_x_00_y_00"),
            attempt_index=1,
            target_run_index=1,
            start_wall_s=0.0,
            start_monotonic_s=0.0,
        )
        statuses = (
            ("done", True),
            ("failed: analyzer crashed", False),
            ("partial: run_summary_failed", False),
            ("not_run", False),
        )
        for analysis_status, expected_ok in statuses:
            with self.subTest(analysis_status=analysis_status):
                record = _record_from_legacy(ctx, {
                    "attempt_id": "wind_x_00_y_00__rep_01__attempt_001",
                    "status": "failed_analysis",
                    "analysis_status": analysis_status,
                })
                self.assertEqual(AttemptStatus.ANALYSIS_FAILED, record.status)
                self.assertEqual(expected_ok, record.analysis_results[0].ok)


if __name__ == "__main__":
    unittest.main()
