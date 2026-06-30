from __future__ import annotations

# pyright: reportMissingImports=false

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sim_ard_gaw.campaigns.wind_matrix import run_one as run_one_impl  # noqa: E402
from sim_ard_gaw.campaigns.wind_world import write_world_wind  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import defaults  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import wind_injection  # noqa: E402


class WindMatrixWindInjectionParityTests(unittest.TestCase):
    def test_parse_wind_echo_matches_legacy(self) -> None:
        samples = [
            "linear_velocity: { x: 4.000 y: -2.000 z: 0.000 } enable_wind: true",
            "enable_wind: false x: 1.0 y: 2.0 z: 3.0",
            "x: 0.010 y: 0.000 z: 0.000",
            "no_wind_payload_here",
        ]
        for sample in samples:
            self.assertEqual(
                run_one_impl.parse_wind_echo(sample),
                wind_injection.parse_wind_echo(sample),
            )

    def test_wind_echo_matches_matches_legacy(self) -> None:
        tol = defaults.WIND_ECHO_TOLERANCE_MPS
        parsed_samples = [
            {"x": 4.0, "y": 8.0, "z": 0.0, "enable_wind": True},
            {"x": 4.0 + tol / 2.0, "y": 8.0 - tol / 2.0, "z": tol / 2.0},
            {"x": 4.0 + tol * 2.0, "y": 8.0, "z": 0.0},
            {"x": 4.0, "y": 8.0, "z": 0.0, "enable_wind": False},
            None,
        ]
        for parsed in parsed_samples:
            self.assertEqual(
                run_one_impl.wind_echo_matches(parsed, 4.0, 8.0),
                wind_injection.wind_echo_matches(parsed, 4.0, 8.0),
            )

    def test_inject_wind_success_first_attempt_matches_legacy(self) -> None:
        x_mps = 4.0
        y_mps = 8.0
        echo_cmd = ["gz", "topic", "-e", "-t", defaults.WIND_TOPIC, "-n", "1"]
        echo_result = {
            "returncode": 0,
            "timed_out": False,
            "stdout": "x: 4.0 y: 8.0 z: 0.0 enable_wind: true",
            "stderr": "",
        }
        completed = subprocess.CompletedProcess(
            args=["gz", "topic"],
            returncode=0,
            stdout="published",
            stderr="",
        )
        with (
            patch.object(run_one_impl, "CAPTURE_WIND_INFO", False),
            patch.object(wind_injection, "CAPTURE_WIND_INFO", False),
            patch.object(run_one_impl, "start_wind_echo", return_value=(object(), echo_cmd)),
            patch.object(wind_injection, "start_wind_echo", return_value=(object(), echo_cmd)),
            patch.object(run_one_impl, "finish_wind_echo", return_value=dict(echo_result)),
            patch.object(wind_injection, "finish_wind_echo", return_value=dict(echo_result)),
            patch.object(run_one_impl.subprocess, "run", return_value=completed),
            patch.object(wind_injection.subprocess, "run", return_value=completed),
            patch.object(run_one_impl, "log", return_value=None),
            patch.object(defaults, "log", return_value=None),
        ):
            legacy = run_one_impl.inject_wind(x_mps, y_mps, strict_echo_verify=True)
            migrated = wind_injection.inject_wind(x_mps, y_mps, strict_echo_verify=True)
        self.assertEqual(legacy, migrated)

    def test_inject_wind_retry_publish_ok_echo_fail_then_success_matches_legacy(self) -> None:
        x_mps = 4.0
        y_mps = 0.0
        echo_cmd = ["gz", "topic", "-e", "-t", defaults.WIND_TOPIC, "-n", "1"]
        completed = subprocess.CompletedProcess(
            args=["gz", "topic"],
            returncode=0,
            stdout="published",
            stderr="",
        )
        legacy_echo_results = [
            {
                "returncode": 0,
                "timed_out": False,
                "stdout": "x: 0.0 y: 0.0 z: 0.0 enable_wind: true",
                "stderr": "",
            },
            {
                "returncode": 0,
                "timed_out": False,
                "stdout": "x: 4.0 y: 0.0 z: 0.0 enable_wind: true",
                "stderr": "",
            },
        ]
        migrated_echo_results = [dict(item) for item in legacy_echo_results]
        with (
            patch.object(run_one_impl, "CAPTURE_WIND_INFO", False),
            patch.object(wind_injection, "CAPTURE_WIND_INFO", False),
            patch.object(run_one_impl, "start_wind_echo", return_value=(object(), echo_cmd)),
            patch.object(wind_injection, "start_wind_echo", return_value=(object(), echo_cmd)),
            patch.object(run_one_impl, "finish_wind_echo", side_effect=legacy_echo_results),
            patch.object(wind_injection, "finish_wind_echo", side_effect=migrated_echo_results),
            patch.object(run_one_impl.subprocess, "run", return_value=completed),
            patch.object(wind_injection.subprocess, "run", return_value=completed),
            patch.object(run_one_impl.time, "sleep", return_value=None),
            patch.object(wind_injection.time, "sleep", return_value=None),
            patch.object(run_one_impl, "log", return_value=None),
            patch.object(defaults, "log", return_value=None),
        ):
            legacy = run_one_impl.inject_wind(x_mps, y_mps, strict_echo_verify=True)
            migrated = wind_injection.inject_wind(x_mps, y_mps, strict_echo_verify=True)
        self.assertEqual(legacy, migrated)
        self.assertEqual(2, migrated["attempt_count"])

    def test_parse_sdf_world_wind_and_preloaded_wind_artifact_match_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_world = defaults.ASSETS_ROOT / "worlds" / "mini_talon_wind_runway.sdf"
            archived_world = root / "archived_world.sdf"
            write_world_wind(source_world, archived_world, x_mps=4.0, y_mps=8.0)

            self.assertEqual(
                run_one_impl.parse_sdf_world_wind(archived_world),
                wind_injection.parse_sdf_world_wind(archived_world),
            )

            with (
                patch.object(run_one_impl, "CAPTURE_WIND_INFO", False),
                patch.object(wind_injection, "CAPTURE_WIND_INFO", False),
            ):
                legacy = run_one_impl.preloaded_wind_artifact(
                    4.0,
                    8.0,
                    source_world=source_world,
                    archived_world=archived_world,
                    refresh_runtime_wind=False,
                )
                migrated = wind_injection.preloaded_wind_artifact(
                    4.0,
                    8.0,
                    source_world=source_world,
                    archived_world=archived_world,
                    refresh_runtime_wind=False,
                )
            self.assertEqual(legacy, migrated)

    def test_preloaded_wind_artifact_refresh_path_matches_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_world = defaults.ASSETS_ROOT / "worlds" / "mini_talon_wind_runway.sdf"
            archived_world = root / "archived_world.sdf"
            write_world_wind(source_world, archived_world, x_mps=0.0, y_mps=4.0)
            refresh_result = {
                "status": "ok",
                "payload": "payload",
                "command": ["gz", "topic"],
                "strict_echo_verification": False,
                "live_wind_info_snapshot": None,
            }
            with (
                patch.object(run_one_impl, "inject_wind", return_value=dict(refresh_result)),
                patch.object(wind_injection, "inject_wind", return_value=dict(refresh_result)),
            ):
                legacy = run_one_impl.preloaded_wind_artifact(
                    0.0,
                    4.0,
                    source_world=source_world,
                    archived_world=archived_world,
                    refresh_runtime_wind=True,
                    refresh_strict_echo_verify=False,
                )
                migrated = wind_injection.preloaded_wind_artifact(
                    0.0,
                    4.0,
                    source_world=source_world,
                    archived_world=archived_world,
                    refresh_runtime_wind=True,
                    refresh_strict_echo_verify=False,
                )
            self.assertEqual(legacy, migrated)


if __name__ == "__main__":
    unittest.main()
