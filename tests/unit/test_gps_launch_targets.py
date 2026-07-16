"""No-SITL structural tests for the dedicated GPS failure launch targets.

These tests never launch SITL or Gazebo. They inspect the governed launcher
source (specific function bodies, not incidental strings elsewhere in the file),
run only `scripts/ops/launch.sh help`, and assert the GPS plugin defaults name
the dedicated identities. They prove:

- `plane-gps` / `gazebo-plane-gps` are discoverable and dispatch to their own
  functions.
- `plane-gps` loads exactly `plane_base.parm -> plane_gps.parm`, wipes EEPROM,
  exposes only the local UDP output, and never appends the airspeed overlay or
  the local plane override.
- `gazebo-plane-gps` uses a dedicated sensor-neutral, east-facing runway world
  and never touches the CTE wind-control path.
- The existing CTE/airspeed targets are unchanged.
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "src" / "sim_ard_gaw" / "launch" / "launch.sh"
OPERATOR_LAUNCH = ROOT / "scripts" / "ops" / "launch.sh"

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure import (  # noqa: E402
    defaults,
    readiness,
)


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


class GpsLaunchTargetSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = LAUNCHER.read_text(encoding="utf-8")

    # --- discovery ---------------------------------------------------------

    def test_help_lists_gps_and_preserves_cte(self) -> None:
        result = subprocess.run(
            [str(OPERATOR_LAUNCH), "help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        out = result.stdout
        self.assertIn("plane-gps", out)
        self.assertIn("gazebo-plane-gps", out)
        # Existing CTE/airspeed targets remain listed.
        self.assertIn("plane-cte", out)
        self.assertIn("gazebo-plane-cte", out)
        self.assertIn("plane-airspeed", out)

    def test_dispatch_routes_to_gps_functions(self) -> None:
        self.assertIn("launch_plane_gps", _dispatch_case(self.source, "plane-gps"))
        self.assertIn(
            "launch_gazebo_plane_gps",
            _dispatch_case(self.source, "gazebo-plane-gps"),
        )
        # plane-gps performs a clean run before launch, like the other SITL
        # targets.
        self.assertIn("cleanup", _dispatch_case(self.source, "plane-gps"))

    # --- SITL structure ----------------------------------------------------

    def test_plane_gps_builder_isolates_stack(self) -> None:
        body = _function_body(self.source, "build_plane_gps_param_args")
        self.assertIn("$PLANE_BASE_PARAM_FILE", body)
        self.assertIn("$PLANE_GPS_PARAM_FILE", body)
        # No airspeed overlay in the GPS builder.
        self.assertNotIn("PLANE_AIRSPEED_PARAM_FILE", body)
        # The local override is never appended as a param file in the GPS lane.
        self.assertNotIn("--add-param-file=\"$PLANE_PARAM_LOCAL_OVERRIDE\"", body)
        # It does not delegate to the shared builder that would append the
        # local override.
        self.assertNotIn("build_plane_param_args", body)

    def test_plane_gps_function_uses_expected_runtime(self) -> None:
        body = _function_body(self.source, "launch_plane_gps")
        self.assertIn("build_plane_gps_param_args", body)
        self.assertIn('build_sitl_runtime_args "plane-gps"', body)
        self.assertIn("--wipe-eeprom", body)
        self.assertIn("--out=udp:127.0.0.1:14551", body)
        self.assertIn("gazebo-plane-gps", body)
        # Never routes through the airspeed/CTE builder or the shared local-override builder.
        self.assertNotIn("build_plane_param_args", body)
        self.assertNotIn("PLANE_AIRSPEED_PARAM_FILE", body)
        # Only the one governed local UDP output is exposed.
        self.assertEqual(body.count("--out="), 1)

    # --- Gazebo structure --------------------------------------------------

    def test_gazebo_plane_gps_uses_dedicated_east_facing_world(self) -> None:
        body = _function_body(self.source, "launch_gazebo_plane_gps")
        self.assertIn("$PLANE_GPS_WORLD", body)
        self.assertNotIn('launch_gazebo_world "$PLANE_WORLD"', body)
        # Does not use the CTE wind world or delegate to the CTE Gazebo path.
        self.assertNotIn("PLANE_WIND_WORLD", body)
        self.assertNotIn("launch_gazebo_plane_cte", body)
        self.assertIn("plane-gps", body)

        world = (ROOT / "assets/worlds/mini_talon_gps_runway.sdf").read_text(
            encoding="utf-8"
        )
        self.assertIn('<world name="mini_talon_gps_runway">', world)
        self.assertIn('<pose degrees="true">0 0 0.2 0 0 0</pose>', world)
        self.assertIn("model://mini_talon", world)
        self.assertNotIn("mini_talon_with_airspeed", world)

    # --- regression: CTE lane unchanged ------------------------------------

    def test_cte_lane_still_uses_airspeed_and_local_override(self) -> None:
        body = _function_body(self.source, "launch_plane_cte")
        self.assertIn("build_plane_param_args", body)
        self.assertIn("$PLANE_AIRSPEED_PARAM_FILE", body)
        # The shared builder (which appends the local override) is unchanged and
        # still appends the local override for historical targets.
        shared = _function_body(self.source, "build_plane_param_args")
        self.assertIn("PLANE_PARAM_LOCAL_OVERRIDE", shared)
        self.assertIn(
            "--add-param-file=\"$PLANE_PARAM_LOCAL_OVERRIDE\"",
            shared,
        )


class GpsPluginTargetDefaultsTests(unittest.TestCase):
    def test_defaults_name_dedicated_targets(self) -> None:
        self.assertEqual("plane-gps", defaults.SITL_TARGET)
        self.assertEqual("gazebo-plane-gps", defaults.GAZEBO_TARGET)

    def test_schema_reports_dedicated_targets(self) -> None:
        schema = defaults.parameter_schema()
        self.assertEqual("plane-gps", schema["sitl_target"])
        self.assertEqual("gazebo-plane-gps", schema["gazebo_target"])

    def test_readiness_reports_dedicated_targets_and_exclusions(self) -> None:
        report = readiness.build_readiness_report()
        stack = report["parameter_stack"]
        self.assertEqual("plane-gps", stack["sitl_target"])
        self.assertEqual("gazebo-plane-gps", stack["gazebo_target"])
        self.assertTrue(stack["local_override_excluded"])
        self.assertTrue(stack["airspeed_overlay_excluded"])
        self.assertFalse(report["ready_for_live_run"])
        # The effective stack is exactly base -> gps overlay.
        effective = stack["effective_param_stack"]
        self.assertEqual(2, len(effective))
        self.assertTrue(effective[0].endswith("plane_base.parm"))
        self.assertTrue(effective[1].endswith("plane_gps.parm"))

    def test_no_gps_default_routes_through_cte(self) -> None:
        self.assertNotIn("cte", defaults.SITL_TARGET)
        self.assertNotIn("cte", defaults.GAZEBO_TARGET)


if __name__ == "__main__":
    unittest.main()
