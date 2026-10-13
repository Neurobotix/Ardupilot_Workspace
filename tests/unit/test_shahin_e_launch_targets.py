"""No-SITL structural tests for the Shahin-E launch targets.

These tests never launch SITL or Gazebo. They inspect the governed launcher
source and run only `scripts/ops/launch.sh help`. They prove:

- `plane-shahin-e` / `gazebo-plane-shahin-e` are discoverable and dispatch to
  their own functions.
- `plane-shahin-e` loads `config/vehicles/shahin_e.parm` ONLY (no
  `plane_base.parm`, no overlay, no local override), wipes EEPROM, uses the
  JSON backend, and exposes only the local UDP output.
- `gazebo-plane-shahin-e` loads `assets/worlds/shahin_e_runway.sdf`, which
  includes the Shahin-E model and not a Mini Talon.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "src" / "sim_ard_gaw" / "launch" / "launch.sh"
OPERATOR_LAUNCH = ROOT / "scripts" / "ops" / "launch.sh"


def _function_body(source: str, name: str) -> str:
    """Return the body of a bash function ``name() { ... }`` by brace matching."""
    match = re.search(rf"(?m)^{re.escape(name)}\(\)\s*\{{", source)
    if match is None:
        raise AssertionError(f"function {name} not found in launcher")
    depth = 0
    start = match.end() - 1  # points at the opening brace
    for idx in range(start, len(source)):
        char = source[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1 : idx]
    raise AssertionError(f"unbalanced braces for function {name}")


def _dispatch_case(source: str, target: str) -> str:
    """Return the dispatch block for a `case` label up to its `;;`."""
    match = re.search(rf"(?m)^\s*{re.escape(target)}\)\s*(.*?);;", source, re.DOTALL)
    if match is None:
        raise AssertionError(f"dispatch case {target}) not found")
    return match.group(1)


class ShahinELaunchTargetSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = LAUNCHER.read_text(encoding="utf-8")

    def test_help_lists_shahin_e_targets(self) -> None:
        result = subprocess.run(
            [str(OPERATOR_LAUNCH), "help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("plane-shahin-e", result.stdout)
        self.assertIn("gazebo-plane-shahin-e", result.stdout)

    def test_dispatch_routes_to_shahin_e_functions(self) -> None:
        sitl = _dispatch_case(self.source, "plane-shahin-e")
        self.assertIn("launch_plane_shahin_e", sitl)
        self.assertIn("cleanup", sitl)
        self.assertIn(
            "launch_gazebo_plane_shahin_e",
            _dispatch_case(self.source, "gazebo-plane-shahin-e"),
        )

    def test_param_path_points_at_shahin_e_parm(self) -> None:
        self.assertIn(
            'SHAHIN_E_PARAM_FILE="$CONFIG_DIR/vehicles/shahin_e.parm"', self.source
        )
        self.assertTrue((ROOT / "config/vehicles/shahin_e.parm").is_file())

    def test_builder_loads_only_shahin_e_parm(self) -> None:
        body = _function_body(self.source, "build_shahin_e_param_args")
        self.assertIn('append_plane_param_file "$SHAHIN_E_PARAM_FILE"', body)
        self.assertEqual(body.count("append_plane_param_file"), 1)
        self.assertNotIn("PLANE_BASE_PARAM_FILE", body)
        self.assertNotIn("--add-param-file=\"$PLANE_PARAM_LOCAL_OVERRIDE\"", body)
        self.assertNotIn("build_plane_param_args", body)

    def test_sitl_function_uses_expected_runtime(self) -> None:
        body = _function_body(self.source, "launch_plane_shahin_e")
        self.assertIn("build_shahin_e_param_args", body)
        self.assertIn('build_sitl_runtime_args "plane-shahin-e"', body)
        self.assertIn("-f JSON", body)
        self.assertIn("--wipe-eeprom", body)
        self.assertIn("--out=udp:127.0.0.1:14551", body)
        self.assertEqual(body.count("--out="), 1)
        self.assertEqual(body.count("--add-param-file"), 0)
        self.assertNotIn("build_plane_param_args", body)
        self.assertNotIn("PLANE_BASE_PARAM_FILE", body)
        self.assertIn("gazebo-plane-shahin-e", body)

    def test_gazebo_function_uses_shahin_e_world(self) -> None:
        self.assertIn(
            'SHAHIN_E_WORLD="$WORLDS_DIR/shahin_e_runway.sdf"', self.source
        )
        body = _function_body(self.source, "launch_gazebo_plane_shahin_e")
        self.assertIn('launch_gazebo_world "$SHAHIN_E_WORLD"', body)
        self.assertNotIn("PLANE_WIND_WORLD", body)
        self.assertNotIn("PLANE_GPS", body)
        self.assertIn("plane-shahin-e", body)

        world = (ROOT / "assets/worlds/shahin_e_runway.sdf").read_text(
            encoding="utf-8"
        )
        self.assertIn('<world name="shahin_e_runway">', world)
        self.assertIn("model://shahin_e", world)
        self.assertNotIn("model://mini_talon", world)


if __name__ == "__main__":
    unittest.main()
