from __future__ import annotations

# pyright: reportMissingImports=false

import sys
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "src" / "sim_ard_gaw"
WIND_MATRIX = RUNTIME / "campaigns" / "wind_matrix"
sys.path.insert(0, str(ROOT / "src"))

from sim_ard_gaw.campaigns.wind_matrix import run_matrix, run_one  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.config import (  # noqa: E402
    WindMatrixConfig,
)


class Phase8RuntimePathTests(unittest.TestCase):
    def test_wind_matrix_defaults_use_owned_workspace_homes(self) -> None:
        self.assertEqual(
            ROOT / "assets" / "missions" / "square_500m_five_laps_loiter5_land.waypoints",
            run_one.MISSION_FILE,
        )
        self.assertEqual(
            ROOT / "config" / "vehicles" / "plane_base.parm",
            run_one.PLANE_BASE_PARAM_FILE,
        )
        self.assertEqual(
            ROOT / "config" / "overlays" / "plane_airspeed.parm",
            run_one.PLANE_AIRSPEED_PARAM_FILE,
        )
        self.assertEqual(
            ROOT / "var" / "logs" / "009_Square_Wind_Matrix_CTE",
            run_one.DEFAULT_CAMPAIGN_ROOT,
        )
        self.assertEqual(
            ROOT / "src" / "sim_ard_gaw" / "analysis" / "true_path_deviation.py",
            run_one.TRUE_PATH_SCRIPT,
        )
        self.assertEqual(
            ROOT / "src" / "sim_ard_gaw" / "launch" / "launch.sh",
            run_matrix.LAUNCH_SCRIPT,
        )
        self.assertEqual(
            ROOT / "assets" / "worlds" / "mini_talon_wind_runway.sdf",
            run_matrix.PLANE_WIND_WORLD,
        )
        self.assertEqual(
            ROOT / "var" / "runs" / "sitl" / "plane-cte" / "logs",
            run_one.sitl_bin_dir(None),
        )

    def test_launcher_uses_owned_directories_instead_of_old_bridge(self) -> None:
        launcher = (RUNTIME / "launch" / "launch.sh").read_text(encoding="utf-8")
        self.assertNotIn("SIM_ARD_GAW_DIR", launcher)
        self.assertIn('CONFIG_DIR="$WORKSPACE_DIR/config"', launcher)
        self.assertIn('WORLDS_DIR="$ASSETS_DIR/worlds"', launcher)
        self.assertIn('BRIDGES_DIR="$WORKSPACE_DIR/src/sim_ard_gaw/bridges"', launcher)
        self.assertIn('ANALYSIS_DIR="$WORKSPACE_DIR/src/sim_ard_gaw/analysis"', launcher)

    def test_retained_matrix_paths_isolate_sitl_state_under_var(self) -> None:
        stack_log_dir = ROOT / "var" / "runs" / "wind-matrix" / "stack"
        matrix_source = (WIND_MATRIX / "run_matrix.py").read_text(encoding="utf-8")

        self.assertEqual(
            stack_log_dir / "attempt_001_sitl_state",
            run_matrix.isolated_sitl_use_dir(stack_log_dir, "attempt_001"),
        )
        self.assertTrue(WindMatrixConfig().isolated_sitl_state)
        self.assertIn("use_dir=sitl_use_dir", matrix_source)
        self.assertIn("sitl_log_dir=sitl_use_dir", matrix_source)

    def test_operator_help_prints_stable_phase8_commands(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts" / "ops" / "launch.sh"), "help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("scripts/ops/launch.sh plane-cte", result.stdout)
        self.assertIn(
            "env/bin/python3 src/sim_ard_gaw/campaigns/wind_matrix/run_one.py",
            result.stdout,
        )
        self.assertNotIn("Terminal 1: ./launch.sh", result.stdout)
        self.assertNotIn("python3 run_one.py", result.stdout)

    def test_cleanup_targets_gazebo_sim_process_tree(self) -> None:
        launcher = (RUNTIME / "launch" / "launch.sh").read_text(encoding="utf-8")
        cleanup = (RUNTIME / "launch" / "cleanup.sh").read_text(encoding="utf-8")

        for source in (launcher, cleanup):
            self.assertIn('pkill -9 -f "[g]z sim"', source)
            self.assertIn('pkill -9 -f "[g]z-sim"', source)
            self.assertIn('pkill -9 -f "[r]uby .*/gz"', source)
            self.assertIn("[s]im_vehicle.py", source)
            self.assertIn("[l]idar_bridge", source)

    def test_phase8_organized_views_are_owned_files_not_symlinks(self) -> None:
        owned_paths = [
            RUNTIME / "launch" / "launch.sh",
            RUNTIME / "bridges" / "lidar_bridge_unified.py",
            RUNTIME / "bridges" / "wind_publisher_altitude.py",
            RUNTIME / "analysis" / "true_path_deviation.py",
            RUNTIME / "analysis" / "square_loiter_mission_metrics.py",
            WIND_MATRIX / "run_one.py",
            WIND_MATRIX / "run_matrix.py",
            WIND_MATRIX / "run_matrix_round_robin.py",
            RUNTIME / "campaigns" / "test_suite",
        ]
        for path in owned_paths:
            with self.subTest(path=path):
                self.assertTrue(path.exists())
                self.assertFalse(path.is_symlink())


if __name__ == "__main__":
    unittest.main()
