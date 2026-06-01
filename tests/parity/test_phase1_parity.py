from __future__ import annotations

# pyright: reportMissingImports=false

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "src" / "sim_ard_gaw" / "compat_scripts"
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
os.environ.setdefault("PYTHONPATH", str(SCRIPTS_DIR))
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from sim_ard_gaw.campaigns.wind_matrix import run_matrix, run_one  # noqa: E402
from test_suite.core.manifest import Manifest  # noqa: E402
from test_suite.core.models import AttemptRecord, TestCase  # noqa: E402
from test_suite.core.scheduler import RoundRobinScheduler  # noqa: E402
from test_suite.plugins.wind_matrix.config import WindMatrixConfig  # noqa: E402
from test_suite.plugins.wind_matrix.manifest import WindMatrixManifest  # noqa: E402


OPTION_RE = re.compile(
    r"^\s+(?:-\w,\s+)?(--[a-z0-9][a-z0-9-]*)(?![=a-z0-9-])",
    re.MULTILINE,
)


def _help_flags(command: list[str]) -> set[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(SRC_DIR), str(SCRIPTS_DIR)])
    output = subprocess.check_output(command, text=True, env=env)
    return set(OPTION_RE.findall(output))


class _FakeManifest(Manifest):
    def __init__(self) -> None:
        self.accepted: dict[str, int] = {}

    def load(self) -> dict[str, Any]:
        return {}

    def save(self, manifest: dict[str, Any]) -> None:
        return None

    def accepted_count(self, case: TestCase) -> int:
        return self.accepted.get(case.case_id, 0)

    def next_attempt_index(self, case: TestCase) -> int:
        return 1

    def append_attempt(self, record: AttemptRecord) -> None:
        return None


class Phase1ParityTests(unittest.TestCase):
    def test_cli_flag_surfaces_match_legacy(self) -> None:
        cases = [
            (
                [sys.executable, str(SCRIPTS_DIR / "run_one.py"), "--help"],
                [sys.executable, "-m", "test_suite.cli.run_case", "--help"],
            ),
            (
                [sys.executable, str(SCRIPTS_DIR / "run_matrix.py"), "--help"],
                [sys.executable, "-m", "test_suite.cli.run_suite", "--help"],
            ),
            (
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "run_matrix_round_robin.py"),
                    "--help",
                ],
                [
                    sys.executable,
                    "-m",
                    "test_suite.cli.run_round_robin",
                    "--help",
                ],
            ),
        ]
        for legacy, new in cases:
            with self.subTest(legacy=legacy[1], new=new[2]):
                legacy_flags = _help_flags(legacy)
                new_flags = _help_flags(new)
                self.assertEqual(set(), legacy_flags - new_flags)
                self.assertEqual(
                    {"--plugin", "--attempt-strategy"},
                    new_flags - legacy_flags,
                )

    def test_suite_cli_does_not_adopt_round_robin_require_analysis_flag(self) -> None:
        suite_flags = _help_flags(
            [sys.executable, "-m", "test_suite.cli.run_suite", "--help"]
        )
        rr_flags = _help_flags(
            [sys.executable, "-m", "test_suite.cli.run_round_robin", "--help"]
        )
        self.assertNotIn("--require-analysis", suite_flags)
        self.assertIn("--require-analysis", rr_flags)

    def test_wind_config_defaults_track_legacy_matrix(self) -> None:
        cfg = WindMatrixConfig()
        self.assertEqual(run_matrix.DEFAULT_STACK_SETTLE, cfg.stack_settle_s)
        self.assertEqual(run_matrix.DEFAULT_RETRY_DELAY, cfg.retry_delay_s)
        self.assertTrue(cfg.launch_stack)

    def test_round_robin_snapshots_one_pass_in_legacy_order(self) -> None:
        cases = [
            TestCase("suite", "c0", acceptance_target_runs=1),
            TestCase("suite", "c1", acceptance_target_runs=1),
            TestCase("suite", "c2", acceptance_target_runs=1),
        ]
        manifest = _FakeManifest()
        scheduler = RoundRobinScheduler(per_attempt_budget_s=10.0, max_passes=1)

        for expected in ("c0", "c1", "c2"):
            decision = scheduler.next_case(cases, manifest)
            case = decision.case
            self.assertIsNotNone(case)
            assert case is not None
            self.assertEqual(expected, case.case_id)
            self.assertEqual(1, decision.metadata["pass_index"])
            self.assertEqual(10.0, decision.metadata["slot_budget_s"])
            manifest.accepted[expected] = 1

        self.assertIsNone(scheduler.next_case(cases, manifest).case)

    def test_static_wind_world_keeps_known_world_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            world_path = Path(temp_dir) / "wind_world.sdf"
            run_matrix.write_static_wind_world(4.0, 8.0, world_path)
            self.assertEqual(
                {"x": 4.0, "y": 8.0, "z": 0.0},
                run_matrix.run_one.parse_sdf_world_wind(world_path),
            )

    def test_wind_runtime_uses_workspace_plugin_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "build" / "ardupilot_gazebo"
            plugin_file = plugin_dir / "libArduPilotPlugin.so"
            plugin_dir.mkdir(parents=True)
            plugin_file.write_text("workspace plugin fixture\n", encoding="ascii")
            with (
                mock.patch.object(run_one, "WORKSPACE_GAZEBO_PLUGIN_DIR", plugin_dir),
                mock.patch.object(run_one, "WORKSPACE_GAZEBO_PLUGIN_FILE", plugin_file),
                mock.patch.dict(
                    os.environ,
                    {"GZ_SIM_SYSTEM_PLUGIN_PATH": "/usr/local/lib/ardupilot_gazebo"},
                ),
            ):
                env = run_one.runtime_env()
        self.assertEqual(str(plugin_dir), env["GZ_SIM_SYSTEM_PLUGIN_PATH"])

    def test_legacy_manifest_does_not_accept_square_only_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            attempt_001 = root / "wind_x_04_y_04" / "runs" / "attempt_001"
            attempt_002 = root / "wind_x_04_y_04" / "runs" / "attempt_002"
            attempt_001.mkdir(parents=True, exist_ok=True)
            attempt_002.mkdir(parents=True, exist_ok=True)
            run_one.save_manifest(root, {
                "campaign_root": str(root),
                "attempts": [
                    {
                        "attempt_id": "wind_x_04_y_04__rep_01__attempt_001",
                        "combo_key": "wind_x_04_y_04",
                        "target_run_index": 1,
                        "attempt_index": 1,
                        "attempt_dir": str(attempt_001),
                        "status": "success_full",
                        "analysis_status": "done",
                    },
                    {
                        "attempt_id": "wind_x_04_y_04__rep_02__attempt_002",
                        "combo_key": "wind_x_04_y_04",
                        "target_run_index": 2,
                        "attempt_index": 2,
                        "attempt_dir": str(attempt_002),
                        "status": "success_square_only",
                        "analysis_status": "done",
                    },
                ],
            })
            case = TestCase(
                suite_name="wind_matrix",
                case_id="wind_x_04_y_04",
                acceptance_target_runs=2,
            )
            strict = WindMatrixManifest(root, accept_square_only=False)
            self.assertEqual(1, strict.accepted_count(case))

            lenient = WindMatrixManifest(root, accept_square_only=True)
            self.assertEqual(2, lenient.accepted_count(case))

    def test_legacy_manifest_partial_alone_is_not_accepted_under_strict_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            attempt_001 = root / "wind_x_00_y_00" / "runs" / "attempt_001"
            attempt_001.mkdir(parents=True, exist_ok=True)
            run_one.save_manifest(root, {
                "campaign_root": str(root),
                "attempts": [
                    {
                        "attempt_id": "wind_x_00_y_00__rep_01__attempt_001",
                        "combo_key": "wind_x_00_y_00",
                        "target_run_index": 1,
                        "attempt_index": 1,
                        "attempt_dir": str(attempt_001),
                        "status": "success_square_only",
                        "analysis_status": "done",
                    },
                    {
                        "attempt_id": "wind_x_00_y_00__rep_02__attempt_002",
                        "combo_key": "wind_x_00_y_00",
                        "status": "failed",
                    },
                    {
                        "attempt_id": "wind_x_00_y_00__rep_03__attempt_003",
                        "combo_key": "wind_x_00_y_00",
                        "status": "failed_analysis",
                    },
                ],
            })
            case = TestCase(
                suite_name="wind_matrix",
                case_id="wind_x_00_y_00",
                acceptance_target_runs=1,
            )
            self.assertEqual(0, WindMatrixManifest(root).accepted_count(case))
            self.assertEqual(
                1, WindMatrixManifest(root, accept_square_only=True).accepted_count(case),
            )

    def test_wind_runtime_rejects_missing_workspace_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "build" / "ardupilot_gazebo"
            plugin_file = plugin_dir / "libArduPilotPlugin.so"
            with (
                mock.patch.object(run_one, "WORKSPACE_GAZEBO_PLUGIN_DIR", plugin_dir),
                mock.patch.object(run_one, "WORKSPACE_GAZEBO_PLUGIN_FILE", plugin_file),
            ):
                with self.assertRaisesRegex(RuntimeError, "fallback is forbidden"):
                    run_one.runtime_env()


if __name__ == "__main__":
    unittest.main()
