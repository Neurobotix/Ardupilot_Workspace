from __future__ import annotations

import json
import math
import sys
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure import defaults  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.analyzers import (  # noqa: E402
    artifact_schema,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.case_generator import (  # noqa: E402
    AirspeedFailureCaseGenerator,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.config import (  # noqa: E402
    AirspeedFailureConfig,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.environment import (  # noqa: E402
    build_run_config,
    build_reference_wind_artifact,
    wind_echo_matches,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.monitor import (  # noqa: E402
    apply_reference_wind_sign_confirmation,
    planned_rtl_reached,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.wind_profiles import (  # noqa: E402
    HEADWIND_EASTBOUND,
    TAILWIND_EASTBOUND,
    WindProfile,
)


def _mission_rows(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or line.startswith("QGC"):
            continue
        rows.append(line.split())
    return rows


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    radius = 6_371_000.0
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


class WindProfileTests(unittest.TestCase):
    def test_direction_neutral_wind_arithmetic(self) -> None:
        self.assertEqual(5.0, HEADWIND_EASTBOUND.expected_arsp_minus_gps_mps)
        self.assertEqual(-5.0, TAILWIND_EASTBOUND.expected_arsp_minus_gps_mps)
        northbound = WindProfile("north", (0.0, 5.0, 0.0), (0.0, 1.0, 0.0))
        self.assertEqual(-5.0, northbound.expected_arsp_minus_gps_mps)

    def test_default_headwind_and_tailwind_echo_sign(self) -> None:
        self.assertEqual("headwind_eastbound", AirspeedFailureConfig().wind_profile_id)
        tailwind = build_reference_wind_artifact(profile=TAILWIND_EASTBOUND)
        self.assertEqual({"x": 5.0, "y": 0.0, "z": 0.0}, tailwind["requested_mps"])
        self.assertEqual(-5.0, tailwind["expected_arsp_minus_gps_mps"])
        right = {"x": 5.0, "y": 0.0, "z": 0.0, "enable_wind": True}
        wrong = {"x": -5.0, "y": 0.0, "z": 0.0, "enable_wind": True}
        self.assertTrue(wind_echo_matches(right, tailwind["requested_mps"]))
        self.assertFalse(wind_echo_matches(wrong, tailwind["requested_mps"]))

    def test_one_way_tailwind_sign_confirmation_requires_only_eastbound(self) -> None:
        artifact = apply_reference_wind_sign_confirmation(
            {"verified": True},
            {
                "eastbound_mean_mps": -5.525,
                "westbound_mean_mps": None,
                "expected_eastbound_mps": -5.0,
                "expected_westbound_mps": 5.0,
            },
            require_westbound=False,
        )
        self.assertTrue(artifact["publication_echo_verified"])
        self.assertTrue(artifact["verified"])
        self.assertEqual("confirmed", artifact["sign_confirmation"]["status"])
        self.assertEqual(
            ["eastbound"],
            artifact["sign_confirmation"]["required_directions"],
        )

    def test_historical_reference_still_requires_westbound(self) -> None:
        artifact = apply_reference_wind_sign_confirmation(
            {"verified": True},
            {
                "eastbound_mean_mps": 5.0,
                "westbound_mean_mps": None,
                "expected_eastbound_mps": 5.0,
                "expected_westbound_mps": -5.0,
            },
            require_westbound=True,
        )
        self.assertFalse(artifact["verified"])
        self.assertEqual(
            "missing_required_direction",
            artifact["sign_confirmation"]["status"],
        )

    def test_out_of_band_required_direction_fails_verification(self) -> None:
        artifact = apply_reference_wind_sign_confirmation(
            {"verified": True},
            {
                "eastbound_mean_mps": -2.0,
                "westbound_mean_mps": None,
                "expected_eastbound_mps": -5.0,
                "expected_westbound_mps": 5.0,
            },
            require_westbound=False,
        )
        self.assertFalse(artifact["verified"])
        self.assertEqual("out_of_band", artifact["sign_confirmation"]["status"])

    def test_planned_rtl_requires_an_actual_late_mission_transition(self) -> None:
        self.assertFalse(planned_rtl_reached(None, 8))
        self.assertFalse(planned_rtl_reached(4, 8))
        self.assertTrue(planned_rtl_reached(8, 8))


class TailwindCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.headwind = {
            case.case_id: case
            for case in AirspeedFailureCaseGenerator(AirspeedFailureConfig()).iter_cases()
        }
        cfg = AirspeedFailureConfig(wind_profile_id="tailwind_eastbound")
        self.tailwind = {
            case.case_id: case for case in AirspeedFailureCaseGenerator(cfg).iter_cases()
        }

    def test_historical_headwind_ids_and_missions_unchanged(self) -> None:
        self.assertEqual(defaults.RAMP_MISSION_FILE, self.headwind[defaults.RAMP_CASE_ID].mission_file)
        self.assertEqual(
            defaults.PULSE_LADDER_MISSION_FILE,
            self.headwind[defaults.PULSE_LADDER_CASE_ID].mission_file,
        )

    def test_tailwind_ids_are_distinct_and_use_long_mission(self) -> None:
        self.assertEqual(
            {
                defaults.TAILWIND_HEALTHY_CASE_ID,
                defaults.TAILWIND_RAMP_CASE_ID,
                defaults.TAILWIND_EXTENDED_RAMP_CASE_ID,
                defaults.TAILWIND_PULSE_LADDER_CASE_ID,
            },
            set(self.tailwind),
        )
        for case in self.tailwind.values():
            self.assertEqual(defaults.EASTBOUND_LONG_SPEED_15_MISSION_FILE, case.mission_file)
            self.assertEqual("tailwind_eastbound", case.parameters["wind_profile"]["profile_id"])
        healthy = self.tailwind[defaults.TAILWIND_HEALTHY_CASE_ID]
        self.assertEqual("protected", healthy.parameters["mechanism_tier"])
        self.assertEqual(15.0, healthy.parameters["expected_ahrs_wind_max"])

    def test_ramp_and_pulse_schedules_are_unchanged(self) -> None:
        pairs = (
            (defaults.RAMP_CASE_ID, defaults.TAILWIND_RAMP_CASE_ID),
            (defaults.EXTENDED_RAMP_CASE_ID, defaults.TAILWIND_EXTENDED_RAMP_CASE_ID),
            (defaults.PULSE_LADDER_CASE_ID, defaults.TAILWIND_PULSE_LADDER_CASE_ID),
        )
        for headwind_id, tailwind_id in pairs:
            self.assertEqual(
                self.headwind[headwind_id].parameters["injection_schedule"],
                self.tailwind[tailwind_id].parameters["injection_schedule"],
            )

    def test_cruise_follow_selects_matching_long_variant(self) -> None:
        cfg = AirspeedFailureConfig(
            wind_profile_id="tailwind_eastbound",
            continuous_speed_source="airspeed_cruise",
        )
        case = AirspeedFailureCaseGenerator(cfg).get_case(
            defaults.TAILWIND_EXTENDED_RAMP_CASE_ID
        )
        self.assertEqual(defaults.EASTBOUND_LONG_CRUISE_FOLLOW_MISSION_FILE, case.mission_file)
        self.assertEqual("airspeed_cruise", case.parameters["speed_source"])

    def test_mechanism_artifact_schema_is_declared(self) -> None:
        schema = artifact_schema()["airspeed_mechanism_gate.json"]
        self.assertIn("mechanism_status", schema["required_fields"])
        self.assertIn("schedule_analysis", schema["required_fields"])
        self.assertTrue(schema["case_specific"])

    def test_run_config_hashes_the_selected_mission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mission = root / "selected.waypoints"
            mission.write_text("QGC WPL 110\n", encoding="utf-8")
            config = AirspeedFailureConfig(
                campaign_root=root,
                wind_profile_id="tailwind_eastbound",
            )
            case = replace(
                self.tailwind[defaults.TAILWIND_HEALTHY_CASE_ID],
                mission_file=mission,
            )
            with patch(
                "sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.environment.source_tree_snapshot",
                return_value={},
            ):
                run_config = build_run_config(
                    config=config,
                    case=case,
                    attempt_index=1,
                    target_run_index=1,
                    param_stack=config.effective_param_stack,
                    sitl_log=root / "sitl.log",
                    gazebo_log=root / "gazebo.log",
                    sitl_use_dir=root / "sitl",
                )
            provenance = run_config["mission_file_provenance"]
            self.assertEqual(str(mission.resolve()), provenance["path"])
            self.assertEqual(mission.stat().st_size, provenance["size_bytes"])
            self.assertEqual(64, len(str(provenance["sha256"])))

    def test_tailwind_live_command_has_separate_phase3_guard(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure",
                "--wind-profile",
                "tailwind_eastbound",
                "--live-case",
                defaults.TAILWIND_HEALTHY_CASE_ID,
                "--confirm-live-phase2",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(SRC)},
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("--confirm-live-tailwind-phase3", proc.stderr)


class MissionAndRecipeTests(unittest.TestCase):
    def test_long_missions_preserve_contract(self) -> None:
        missions = (
            (defaults.EASTBOUND_LONG_SPEED_15_MISSION_FILE, True),
            (defaults.EASTBOUND_LONG_CRUISE_FOLLOW_MISSION_FILE, False),
        )
        for path, expects_do15 in missions:
            rows = _mission_rows(path)
            self.assertEqual([0, 1, 2, 3, 4], [int(row[0]) for row in rows])
            self.assertEqual([100.0, 100.0], [float(rows[3][10]), float(rows[4][10])])
            has_do15 = any(int(row[3]) == 178 and float(row[5]) == 15.0 for row in rows)
            self.assertEqual(expects_do15, has_do15)
            self.assertFalse(any(int(row[3]) == 20 for row in rows))
            leg = _distance_m(
                (float(rows[3][8]), float(rows[3][9])),
                (float(rows[4][8]), float(rows[4][9])),
            )
            self.assertAlmostEqual(36_000.0, leg, delta=5.0)

    def test_36km_satisfies_approved_tailwind_duration_margin(self) -> None:
        pulse_required = 20.52636143234041 * 1560.0 * 1.10
        self.assertGreaterEqual(36_000.0, pulse_required)

    def test_counterpart_recipe_totals_17_and_excludes_legacy(self) -> None:
        path = ROOT / "config/campaigns/airspeed_failure_tailwind_counterparts.json"
        recipe = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(17, sum(int(cell["attempts"]) for cell in recipe["cells"]))
        self.assertEqual("tailwind_eastbound", recipe["wind_profile_id"])
        self.assertEqual(1, len(recipe["excluded_historical_roots"]))


if __name__ == "__main__":
    unittest.main()
