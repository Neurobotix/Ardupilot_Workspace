from __future__ import annotations

import importlib.abc
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.campaigns.test_suite.cli._registry import PLUGINS  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.core.models import (  # noqa: E402
    AnalysisResult,
    AttemptRecord,
    AttemptStatus,
    Verdict,
    VerdictClass,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure import defaults, glitch  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.analyzers import (  # noqa: E402
    artifact_schema,
    classify_observation,
    required_attempt_artifacts,
    validate_artifact_against_schema,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.case_generator import (  # noqa: E402
    GpsFailureCaseGenerator,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.config import (  # noqa: E402
    GpsFailureConfig,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.manifest import (  # noqa: E402
    GpsFailureManifest,
    accepted_observation_from_attempt,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.monitor import (  # noqa: E402
    first_seq4_edge_after_armed_auto_front_half,
    first_seq4_edge_after_front_half,
    trigger_metadata,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.plugin import (  # noqa: E402
    build_plugin,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.stimulus import (  # noqa: E402
    build_injection_artifact,
    build_live_plan_preview,
    compare_readback,
)


EXPECTED_SIM_GPS_PARAMS = [
    "SIM_GPS1_ENABLE",
    "SIM_GPS1_GLTCH_X",
    "SIM_GPS1_GLTCH_Y",
    "SIM_GPS1_GLTCH_Z",
    "SIM_GPS1_JAM",
]

EXPECTED_SOURCE_DEFAULTS = {
    "SIM_GPS1_ENABLE": 1.0,
    "SIM_GPS1_GLTCH_X": 0.0,
    "SIM_GPS1_GLTCH_Y": 0.0,
    "SIM_GPS1_GLTCH_Z": 0.0,
    "SIM_GPS1_JAM": 0.0,
}

EXPECTED_PARAM_STACK = [
    ROOT / "config/vehicles/plane_base.parm",
    ROOT / "config/overlays/plane_gps.parm",
]


def _mission_rows(path: Path) -> tuple[str, list[list[str]]]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return lines[0], [line.split() for line in lines[1:]]


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return radius_m * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _parse_param_file(path: Path) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        content = raw_line.split("#", 1)[0].strip()
        if not content:
            continue
        fields = content.split()
        if len(fields) != 2:
            raise ValueError(f"{path}:{line_number}: expected name and numeric value")
        name, raw_value = fields
        if name in parsed:
            raise ValueError(f"{path}:{line_number}: duplicate parameter {name}")
        parsed[name] = float(raw_value)
    return parsed


def _cases(config: GpsFailureConfig | None = None):
    return list(GpsFailureCaseGenerator(config or GpsFailureConfig()).iter_cases())


def _valid_observation(**updates: Any) -> dict[str, Any]:
    """A cleanly measured nominal observation with substantive behavior evidence.

    Nominal must be established by positive evidence (fused, gap within band, no
    growth, attitude in band, no failsafe/mode change) — never by the absence of
    an adverse flag.
    """
    observation: dict[str, Any] = {
        "injection_triggered": True,
        "injection_readback_ok": True,
        "post_injection_s": 90.0,
        "required_artifacts_present": True,
        "mechanism_evidence": True,
        "fused": True,
        "horizontal_gap_m": 0.5,
        "gap_growing": False,
        "gap_within_nominal_band": True,
        "attitude_in_band": True,
        "failsafe": False,
        "mode_change": False,
    }
    observation.update(updates)
    return observation


def _accepted_attempt(**updates: Any) -> dict[str, Any]:
    attempt: dict[str, Any] = {
        "verdict": {
            "class": "success",
            "reason": "loss_of_control",
            "metadata": {"accepted_observation": True},
        },
        "analysis_results": [
            {
                "ok": True,
                "summary": {
                    "accepted_observation": True,
                    "behavior_class": "loss_of_control",
                    "observation_quality_class": "valid_bad_behavior",
                },
            }
        ],
    }
    attempt.update(updates)
    return attempt


class GpsFailurePhase1Tests(unittest.TestCase):
    def test_mission_asset_matches_locked_five_item_geometry(self) -> None:
        mission_path = ROOT / "assets/missions/gps_failure_behavior_mission.waypoints"
        self.assertTrue(mission_path.is_file())
        header, rows = _mission_rows(mission_path)
        self.assertEqual("QGC WPL 110", header)
        self.assertTrue(all(len(row) == 12 for row in rows))
        self.assertEqual(list(range(5)), [int(row[0]) for row in rows])

        template_path = (
            ROOT
            / "assets/missions/airspeed_failure_eastbound_long_speed_15_mission.waypoints"
        )
        _, template_rows = _mission_rows(template_path)
        self.assertEqual(template_rows[1:], rows[1:])

        by_seq = {int(row[0]): row for row in rows}
        self.assertEqual(22, int(by_seq[1][3]))
        self.assertEqual(178, int(by_seq[2][3]))
        self.assertEqual(15.0, float(by_seq[2][5]))
        self.assertEqual(16, int(by_seq[3][3]))
        self.assertEqual(16, int(by_seq[4][3]))
        self.assertNotIn(20, [int(row[3]) for row in rows])

        seq3 = by_seq[3]
        seq4 = by_seq[4]
        leg_distance_m = _distance_m(
            float(seq3[8]),
            float(seq3[9]),
            float(seq4[8]),
            float(seq4[9]),
        )
        self.assertGreaterEqual(leg_distance_m, 35_000.0)
        self.assertLessEqual(leg_distance_m, 37_000.0)
        self.assertGreater(float(seq4[9]), float(seq3[9]))
        self.assertEqual(4, max(by_seq))

    def test_defaults_and_generated_cases_use_gps_mission_asset(self) -> None:
        expected = ROOT / "assets/missions/gps_failure_behavior_mission.waypoints"
        self.assertEqual(expected, defaults.MISSION_FILE)
        self.assertTrue(all(case.mission_file == expected for case in _cases()))

    def test_gps_overlay_contains_locked_values_without_airspeed_params(self) -> None:
        overlay = ROOT / "config/overlays/plane_gps.parm"
        self.assertTrue(overlay.is_file())
        params = _parse_param_file(overlay)
        self.assertEqual(
            {
                "EK3_POS_I_GATE": 500.0,
                "EK3_GLITCH_RAD": 25.0,
                "FS_EKF_THRESH": 0.8,
                "EK3_GPS_CHECK": 31.0,
            },
            {
                name: params[name]
                for name in (
                    "EK3_POS_I_GATE",
                    "EK3_GLITCH_RAD",
                    "FS_EKF_THRESH",
                    "EK3_GPS_CHECK",
                )
            },
        )
        self.assertEqual(
            {
                "EK3_SRC1_POSXY": 3.0,
                "EK3_SRC1_VELXY": 3.0,
                "EK3_SRC1_POSZ": 1.0,
                "EK3_SRC1_VELZ": 3.0,
                "EK3_SRC1_YAW": 1.0,
            },
            {
                name: params[name]
                for name in (
                    "EK3_SRC1_POSXY",
                    "EK3_SRC1_VELXY",
                    "EK3_SRC1_POSZ",
                    "EK3_SRC1_VELZ",
                    "EK3_SRC1_YAW",
                )
            },
        )
        self.assertEqual(
            {
                "SIM_WIND_SPD": 0.0,
                "SIM_WIND_DIR": 180.0,
                "SIM_WIND_TURB": 0.0,
            },
            {
                name: params[name]
                for name in ("SIM_WIND_SPD", "SIM_WIND_DIR", "SIM_WIND_TURB")
            },
        )
        self.assertFalse(
            any(name.startswith(("ARSPD_", "AIRSPEED_")) for name in params)
        )

    def test_param_parser_rejects_duplicate_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "duplicate.parm"
            path.write_text(
                "EK3_POS_I_GATE 500\nEK3_POS_I_GATE 500\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate parameter"):
                _parse_param_file(path)

    def test_default_param_stack_and_explicit_override(self) -> None:
        config = GpsFailureConfig()
        self.assertEqual(EXPECTED_PARAM_STACK, config.effective_param_stack)
        override = [Path("/tmp/custom_base.parm"), Path("/tmp/custom_overlay.parm")]
        self.assertEqual(
            override,
            GpsFailureConfig(param_file_stack=override).effective_param_stack,
        )

    def test_case_list_includes_locked_catalog(self) -> None:
        case_ids = [case.case_id for case in _cases()]
        self.assertEqual("nominal", case_ids[0])
        self.assertEqual(
            [
                "slow_drift_0p2_mps",
                "slow_drift_0p5_mps",
                "slow_drift_1p0_mps",
                "slow_drift_2p0_mps",
                "slow_drift_4p0_mps",
                "slow_drift_8p0_mps",
                "slow_drift_accumulation_ramp",
            ],
            [case_id for case_id in case_ids if case_id.startswith("slow_drift_")],
        )
        self.assertEqual(
            [
                "step_glitch_010m",
                "step_glitch_025m",
                "step_glitch_050m",
                "step_glitch_100m",
                "step_glitch_200m",
                "step_glitch_500m",
            ],
            [case_id for case_id in case_ids if case_id.startswith("step_glitch_")],
        )
        self.assertEqual(
            [
                "hard_denial_05s",
                "hard_denial_15s",
                "hard_denial_30s",
                "hard_denial_60s",
            ],
            [case_id for case_id in case_ids if case_id.startswith("hard_denial_")],
        )
        self.assertEqual(
            [
                "jamming_repeat_01",
                "jamming_repeat_02",
                "jamming_repeat_03",
                "jamming_repeat_04",
                "jamming_repeat_05",
            ],
            [case_id for case_id in case_ids if case_id.startswith("jamming_repeat_")],
        )
        self.assertEqual(
            {"nominal", "slow_drift", "step_glitch", "hard_denial", "jamming"},
            {case.parameters["fault_type"] for case in _cases()},
        )
        self.assertEqual(23, len(case_ids))
        self.assertEqual(len(case_ids), len(set(case_ids)))

    def test_dry_run_prints_phase1_no_launch_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure",
                "--dry-run",
                "--case",
                "hard_denial_15s",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual("phase1_no_sitl", data["phase"])
        self.assertTrue(data["plugin_constructed"])
        self.assertFalse(data["launch_performed"])
        self.assertFalse(data["live_readback_performed"])
        self.assertEqual("hard_denial", data["case"]["parameters"]["fault_type"])
        self.assertEqual(
            [str(path) for path in EXPECTED_PARAM_STACK],
            data["effective_param_stack"],
        )
        self.assertEqual(
            [str(path) for path in EXPECTED_PARAM_STACK],
            data["parameter_schema"]["phase1_param_stack"],
        )

    def test_probe_schema_reports_two_file_default_stack(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure",
                "--probe-schema",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        schema = json.loads(proc.stdout)
        self.assertEqual(
            [str(path) for path in EXPECTED_PARAM_STACK],
            schema["phase1_param_stack"],
        )

    def test_cli_list_cases_outputs_case_ids_only(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure",
                "--list-cases",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        lines = proc.stdout.splitlines()
        self.assertEqual([case.case_id for case in _cases()], lines)
        self.assertNotIn("{", proc.stdout)

    def test_cli_action_conflicts_exit_nonzero(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        base = [
            sys.executable,
            "-m",
            "sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure",
        ]
        for args in (
            ["--list-cases", "--probe-schema"],
            ["--dry-run", "--case", "nominal", "--list-cases"],
            ["--probe-schema", "--case", "nominal"],
            ["--list-cases", "--preview-elapsed-s", "90"],
        ):
            with self.subTest(args=args):
                proc = subprocess.run(
                    [*base, *args],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(0, proc.returncode)
                self.assertEqual("", proc.stdout)

    def test_glitch_conversion_maps_metres_to_degrees_with_signs(self) -> None:
        north = glitch.meters_east_north_to_glitch_degrees(
            east_m=0.0,
            north_m=111_320.0,
            latitude_deg=0.0,
        )
        self.assertAlmostEqual(1.0, north["SIM_GPS1_GLTCH_X"], places=9)
        self.assertAlmostEqual(0.0, north["SIM_GPS1_GLTCH_Y"], places=9)

        east = glitch.meters_east_north_to_glitch_degrees(
            east_m=111_320.0,
            north_m=0.0,
            latitude_deg=0.0,
        )
        self.assertAlmostEqual(0.0, east["SIM_GPS1_GLTCH_X"], places=9)
        self.assertAlmostEqual(1.0, east["SIM_GPS1_GLTCH_Y"], places=9)
        self.assertEqual(0.0, east["SIM_GPS1_GLTCH_Z"])

        east_at_60 = glitch.meters_east_north_to_glitch_degrees(
            east_m=111_320.0,
            north_m=0.0,
            latitude_deg=60.0,
        )
        self.assertGreater(east_at_60["SIM_GPS1_GLTCH_Y"], east["SIM_GPS1_GLTCH_Y"])

        signed = glitch.meters_east_north_to_glitch_degrees(
            east_m=25.0,
            north_m=50.0,
            latitude_deg=0.0,
        )
        self.assertGreater(signed["SIM_GPS1_GLTCH_X"], 0.0)
        self.assertGreater(signed["SIM_GPS1_GLTCH_Y"], 0.0)
        with self.assertRaisesRegex(ValueError, "too close to a pole"):
            glitch.meters_east_north_to_glitch_degrees(1.0, 0.0, 90.0)

    def test_glitch_helpers_reject_nan_and_infinity(self) -> None:
        with self.assertRaisesRegex(ValueError, "latitude_deg must be finite"):
            glitch.meters_east_north_to_glitch_degrees(0.0, 0.0, math.nan)
        with self.assertRaisesRegex(ValueError, "latitude_deg must be finite"):
            glitch.meters_east_north_to_glitch_degrees(0.0, 0.0, math.inf)
        with self.assertRaisesRegex(ValueError, "east_m must be finite"):
            glitch.meters_east_north_to_glitch_degrees(math.nan, 0.0, 0.0)
        with self.assertRaisesRegex(ValueError, "north_m must be finite"):
            glitch.meters_east_north_to_glitch_degrees(0.0, math.nan, 0.0)
        with self.assertRaisesRegex(ValueError, "rate_mps must be finite"):
            glitch.slow_drift_payload(math.nan, 90.0, 0.0)
        with self.assertRaisesRegex(ValueError, "elapsed_s must be finite"):
            glitch.slow_drift_payload(0.5, math.nan, 0.0)

    def test_step_glitch_recipe_and_payload_preview_are_degrees(self) -> None:
        payload = glitch.step_glitch_payload(100.0, latitude_deg=0.0)
        self.assertAlmostEqual(0.0, payload["SIM_GPS1_GLTCH_X"], places=12)
        self.assertAlmostEqual(100.0 / 111_320.0, payload["SIM_GPS1_GLTCH_Y"], places=12)

        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("step_glitch_100m")
        recipe = case.parameters["fault_recipe"]
        self.assertEqual("local tangent frame: +east metres, +north metres", recipe["frame"])
        self.assertIn("positive east", recipe["sign_convention"])
        self.assertEqual(0.0, recipe["example_reference_latitude_deg"])
        self.assertAlmostEqual(
            100.0 / 111_320.0,
            recipe["example_resolved_payload"]["SIM_GPS1_GLTCH_Y"],
            places=12,
        )

    def test_slow_drift_payload_and_dry_run_preview(self) -> None:
        payload = glitch.slow_drift_payload(0.5, elapsed_s=90.0, latitude_deg=0.0)
        self.assertAlmostEqual(0.0, payload["SIM_GPS1_GLTCH_X"], places=12)
        self.assertAlmostEqual(45.0 / 111_320.0, payload["SIM_GPS1_GLTCH_Y"], places=12)

        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        base_cmd = [
            sys.executable,
            "-m",
            "sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure",
            "--dry-run",
            "--case",
            "slow_drift_0p5_mps",
        ]
        without_ref = subprocess.run(
            base_cmd,
            cwd=ROOT,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        data_without_ref = json.loads(without_ref.stdout)
        self.assertNotIn("resolved_payload_preview", data_without_ref)
        self.assertEqual({}, data_without_ref["case"]["parameters"]["injection_payload"])

        with_ref = subprocess.run(
            [*base_cmd, "--reference-latitude-deg", "0", "--preview-elapsed-s", "90"],
            cwd=ROOT,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        data_with_ref = json.loads(with_ref.stdout)
        preview = data_with_ref["resolved_payload_preview"]
        self.assertTrue(preview["not_live_payload"])
        self.assertEqual(0.0, preview["latitude_deg"])
        self.assertEqual(90.0, preview["elapsed_s"])
        self.assertAlmostEqual(45.0, preview["offset_m"], places=12)
        self.assertAlmostEqual(
            45.0 / 111_320.0,
            preview["payload"]["SIM_GPS1_GLTCH_Y"],
            places=12,
        )

    def test_stimulus_live_plan_preview_is_plan_only_and_no_launch(self) -> None:
        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case(
            "slow_drift_0p5_mps"
        )
        plan = build_live_plan_preview(
            case,
            {
                "trigger_latitude_deg": 0.0,
                "trigger_time_s": 12.0,
                "elapsed_since_trigger_s": 90.0,
            },
        )

        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertFalse(plan.launch_performed)
        self.assertFalse(plan.live_readback_performed)
        self.assertEqual(set(plan.injection_payload), set(plan.readback_rules))

    def test_dry_run_preview_rejects_nan_inputs_without_nan_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        base_cmd = [
            sys.executable,
            "-m",
            "sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure",
            "--dry-run",
            "--case",
            "slow_drift_0p5_mps",
        ]
        for args in (
            ["--reference-latitude-deg", "nan", "--preview-elapsed-s", "90"],
            ["--reference-latitude-deg", "0", "--preview-elapsed-s", "nan"],
        ):
            with self.subTest(args=args):
                proc = subprocess.run(
                    [*base_cmd, *args],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(0, proc.returncode)
                self.assertEqual("", proc.stdout)
                self.assertNotIn("NaN", proc.stdout)
                self.assertNotIn("Infinity", proc.stdout)

    def test_continuous_accumulation_case_is_metadata_only_no_reset(self) -> None:
        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case(
            "slow_drift_accumulation_ramp"
        )
        recipe = case.parameters["fault_recipe"]
        self.assertEqual("slow_drift", case.parameters["fault_type"])
        self.assertEqual("sim_gps_glitch_slow_drift_accumulation", case.stimulus_name)
        self.assertTrue(recipe["continuous_ramp"])
        self.assertFalse(recipe["in_flight_reset"])
        self.assertTrue(recipe["fresh_flight_required"])
        self.assertTrue(recipe["requires_live_resolution"])
        self.assertEqual(list(defaults.DRIFT_RATES_MPS), recipe["drift_rates_mps"])
        self.assertIn("accumulation/endurance", recipe["measurement_role"])
        self.assertIn("not independent knee points", recipe["measurement_role"])
        self.assertEqual([], case.parameters["injection_schedule"])

    def test_gps_drift_has_no_airspeed_style_reset_ladder_and_anchors_unchanged(self) -> None:
        generator = GpsFailureCaseGenerator(GpsFailureConfig())
        for case in generator.iter_cases():
            if case.parameters["fault_type"] != "slow_drift":
                continue
            self.assertEqual({}, case.parameters["injection_payload"])
            self.assertEqual([], case.parameters["injection_schedule"])
            self.assertNotIn("pulse_ladder", json.dumps(case.parameters))

        hard_denial = generator.get_case("hard_denial_15s")
        self.assertEqual({"SIM_GPS1_ENABLE": 0.0}, hard_denial.parameters["injection_payload"])
        self.assertEqual(
            {"SIM_GPS1_ENABLE": 1.0},
            hard_denial.parameters["fault_recipe"]["restore_payload"],
        )
        jamming = generator.get_case("jamming_repeat_01")
        self.assertEqual({"SIM_GPS1_JAM": 1.0}, jamming.parameters["injection_payload"])

    def test_parameter_schema_includes_required_params_and_reset_defaults(self) -> None:
        schema = defaults.parameter_schema()
        self.assertEqual(EXPECTED_SIM_GPS_PARAMS, list(defaults.REQUIRED_SIM_GPS_PARAMS))
        self.assertEqual(EXPECTED_SIM_GPS_PARAMS, schema["required_names"])
        self.assertEqual(EXPECTED_SOURCE_DEFAULTS, defaults.SOURCE_DEFAULTS)
        self.assertEqual(EXPECTED_SOURCE_DEFAULTS, schema["source_defaults"])
        self.assertEqual(["analysis_incomplete"], schema["analysis_state_classes"])
        self.assertNotIn("analysis_incomplete", schema["behavior_classes"])
        self.assertNotIn("planned_param_stack", schema)
        self.assertEqual(
            [str(path) for path in EXPECTED_PARAM_STACK],
            schema["phase1_param_stack"],
        )
        defaults.validate_required_param_names(schema["required_names"])
        with self.assertRaisesRegex(ValueError, "Missing required"):
            defaults.validate_required_param_names(["SIM_GPS1_ENABLE"])

        for case in _cases():
            self.assertEqual(EXPECTED_SOURCE_DEFAULTS, case.parameters["reset_payload"])

        self.assertEqual(90.0, defaults.MIN_POST_INJECTION_S)
        self.assertIsNot(defaults.PARAMETER_METADATA, schema["metadata"])
        hard_denial = GpsFailureCaseGenerator(GpsFailureConfig()).get_case(
            "hard_denial_15s"
        )
        requirements = hard_denial.parameters["acceptance_requirements"]
        self.assertEqual(90.0, requirements["min_post_injection_s"])
        self.assertEqual(
            [
                "gps_injection.json",
                "gps_behavior_summary.json",
                "ekf_innovation_metrics.json",
                "truth_vs_belief.json",
                "mode_timeline.json",
                "attitude_altitude_envelope.json",
            ],
            requirements["required_artifacts"],
        )

    def test_trigger_metadata_is_seq4_first_edge_after_front_half(self) -> None:
        meta = trigger_metadata()
        self.assertEqual("MISSION_CURRENT", meta["source"])
        self.assertEqual(4, meta["seq"])
        self.assertEqual("first seq==4 after front-half progress", meta["edge"])
        self.assertEqual([1, 2, 3], meta["front_half_required_sequences"])
        self.assertTrue(first_seq4_edge_after_front_half([1, 2, 3, 4]))
        self.assertFalse(first_seq4_edge_after_front_half([1, 4]))
        self.assertFalse(first_seq4_edge_after_front_half([1, 2, 4]))
        self.assertFalse(first_seq4_edge_after_front_half([4, 1, 2, 3]))

    def test_structured_trigger_requires_armed_auto_front_half_before_seq4(self) -> None:
        good = [
            {"seq": 1, "armed": True, "mode": "AUTO"},
            {"seq": 1, "armed": True, "mode": "AUTO"},
            {"seq": 2, "armed": True, "mode": "AUTO"},
            {"seq": 3, "armed": True, "mode": "AUTO"},
            {"seq": 4, "armed": True, "mode": "AUTO"},
            {"seq": 4, "armed": True, "mode": "AUTO"},
        ]
        self.assertTrue(first_seq4_edge_after_armed_auto_front_half(good))
        self.assertFalse(first_seq4_edge_after_armed_auto_front_half(["bad"]))
        self.assertFalse(first_seq4_edge_after_armed_auto_front_half([{}]))
        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half(
                [{"seq": "bad", "armed": True, "mode": "AUTO"}]
            )
        )
        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half(
                [{"seq": 4, "armed": True, "mode": "AUTO"}]
            )
        )
        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half(
                [
                    {"seq": 1, "armed": False, "mode": "AUTO"},
                    {"seq": 2, "armed": True, "mode": "AUTO"},
                    {"seq": 3, "armed": True, "mode": "AUTO"},
                    {"seq": 4, "armed": True, "mode": "AUTO"},
                ]
            )
        )
        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half(
                [
                    {"seq": 1, "armed": True, "mode": "AUTO"},
                    {"seq": 2, "armed": True, "mode": "MANUAL"},
                    {"seq": 3, "armed": True, "mode": "AUTO"},
                    {"seq": 4, "armed": True, "mode": "AUTO"},
                ]
            )
        )
        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half(
                [
                    {"seq": 4, "armed": True, "mode": "AUTO"},
                    {"seq": 1, "armed": True, "mode": "AUTO"},
                    {"seq": 2, "armed": True, "mode": "AUTO"},
                    {"seq": 3, "armed": True, "mode": "AUTO"},
                ]
            )
        )

    def test_trigger_rejects_regressive_and_skipped_sequences(self) -> None:
        armed = lambda seq: {"seq": seq, "armed": True, "mode": "AUTO"}
        # A regression to a lower mission-current seq (1,2,3,2,4) is invalid.
        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half(
                [armed(1), armed(2), armed(3), armed(2), armed(4)]
            )
        )
        # A skipped front-half seq (1,3,4) is invalid.
        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half([armed(1), armed(3), armed(4)])
        )
        # Jumping straight past the next required seq (1,2,4) is invalid.
        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half([armed(1), armed(2), armed(4)])
        )
        # A repeated MISSION_CURRENT for the *current* seq is benign telemetry
        # and still validates (the stream reports the same seq repeatedly).
        self.assertTrue(
            first_seq4_edge_after_armed_auto_front_half(
                [armed(1), armed(1), armed(2), armed(2), armed(3), armed(4)]
            )
        )
        # A duplicate that regresses after progress (1,2,3,4 then back to 2) is
        # caught before it can re-open the front half.
        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half(
                [armed(1), armed(2), armed(2), armed(3), armed(2), armed(4)]
            )
        )

    def test_artifact_schema_uses_locked_gps_names(self) -> None:
        schemas = artifact_schema()
        self.assertIn("gps_behavior_summary.json", schemas)
        self.assertIn("ekf_innovation_metrics.json", schemas)
        self.assertIn("truth_vs_belief.json", schemas)
        self.assertIn("mode_timeline.json", schemas)
        self.assertIn("attitude_altitude_envelope.json", schemas)
        self.assertNotIn("gps_signal_metrics.json", schemas)
        self.assertNotIn("altitude_envelope.json", schemas)

    def test_required_artifact_set_is_exact_and_locked(self) -> None:
        self.assertEqual(
            [
                "gps_injection.json",
                "gps_behavior_summary.json",
                "ekf_innovation_metrics.json",
                "truth_vs_belief.json",
                "mode_timeline.json",
                "attitude_altitude_envelope.json",
            ],
            required_attempt_artifacts(),
        )
        self.assertEqual(
            list(defaults.REQUIRED_ATTEMPT_ARTIFACTS), required_attempt_artifacts()
        )

    def test_gps_injection_json_has_schema_covering_required_fields(self) -> None:
        schemas = artifact_schema()
        self.assertIn("gps_injection.json", schemas)
        required_fields = schemas["gps_injection.json"]["required_fields"]
        for field_name in (
            "case_id",
            "fault_type",
            "requested_payload",
            "injection_schedule",
            "fault_recipe",
            "payload_resolution",
            "reset_payload",
            "trigger",
            "readback_rules",
            "readback_status_shape",
            "live_plan_contract",
        ):
            self.assertIn(field_name, required_fields)

    def test_every_required_artifact_has_a_schema_entry(self) -> None:
        schemas = artifact_schema()
        for name in required_attempt_artifacts():
            self.assertIn(name, schemas, name)

    def test_produced_injection_artifact_satisfies_declared_schema(self) -> None:
        for case in _cases():
            with self.subTest(case_id=case.case_id):
                artifact = build_injection_artifact(case)
                self.assertEqual(
                    [],
                    validate_artifact_against_schema("gps_injection.json", artifact),
                )
                # The produced artifact must serialize as strict JSON.
                encoded = json.dumps(artifact, allow_nan=False, sort_keys=True)
                self.assertNotIn("NaN", encoded)
                self.assertNotIn("Infinity", encoded)

    def test_injection_artifact_missing_critical_fields_fails_validation(self) -> None:
        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("hard_denial_15s")
        artifact = build_injection_artifact(case)
        for critical in ("trigger", "readback_rules", "requested_payload"):
            with self.subTest(critical=critical):
                broken = {k: v for k, v in artifact.items() if k != critical}
                missing = validate_artifact_against_schema("gps_injection.json", broken)
                self.assertIn(critical, missing)

    def test_unknown_artifact_name_fails_closed(self) -> None:
        self.assertEqual(
            ["<unknown-artifact:not_a_real_artifact.json>"],
            validate_artifact_against_schema("not_a_real_artifact.json", {}),
        )

    def test_plugin_constructs_through_registry_without_launch(self) -> None:
        self.assertIn("gps_failure", PLUGINS)
        plugin = cast(Any, PLUGINS["gps_failure"](launch_stack=False))
        first_case = next(iter(plugin.case_generator.iter_cases()))
        self.assertEqual(defaults.SUITE_NAME, first_case.suite_name)
        self.assertFalse(plugin.config.launch_stack)

    def test_manifest_accepted_count_counts_accepted_observations_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = GpsFailureManifest(root)
            case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case(
                "jamming_repeat_01"
            )
            accepted = AttemptRecord(
                attempt_id="accepted",
                suite_name=case.suite_name,
                case_id=case.case_id,
                target_run_index=1,
                attempt_index=1,
                status=AttemptStatus.SUCCESS,
                verdict=Verdict(
                    klass=VerdictClass.SUCCESS,
                    reason="loss_of_control",
                    retryable=False,
                    metadata={"accepted_observation": True},
                ),
                analysis_results=[
                    AnalysisResult(
                        analyzer_name="gps",
                        ok=True,
                        summary={
                            "accepted_observation": True,
                            "behavior_class": "loss_of_control",
                        },
                    )
                ],
            )
            rejected = AttemptRecord(
                attempt_id="rejected",
                suite_name=case.suite_name,
                case_id=case.case_id,
                target_run_index=1,
                attempt_index=2,
                status=AttemptStatus.ANALYSIS_FAILED,
                verdict=Verdict(
                    klass=VerdictClass.ANALYSIS_FAILED,
                    reason="pre_injection_failure",
                    retryable=True,
                    metadata={"accepted_observation": False},
                ),
            )
            manifest.append_attempt(accepted)
            manifest.append_attempt(rejected)
            self.assertEqual(1, manifest.accepted_count(case))

    def test_behavior_class_is_characterized_not_gated(self) -> None:
        base = _valid_observation()
        nominal = classify_observation(base)
        self.assertTrue(nominal["accepted_observation"])
        self.assertEqual("nominal", nominal["behavior_class"])

        result = classify_observation({**base, "loss_of_control": True})
        self.assertTrue(result["accepted_observation"])
        self.assertEqual("loss_of_control", result["behavior_class"])
        silent = classify_observation(
            {
                **base,
                "fused": True,
                "horizontal_gap_m": 120.0,
                "gap_growing": True,
                "gap_within_nominal_band": False,
                "failsafe": False,
            }
        )
        self.assertTrue(silent["accepted_observation"])
        self.assertEqual("silent_drift", silent["behavior_class"])

    def test_behavior_evidence_marker_only_is_rejected_as_incomplete(self) -> None:
        # A bare marker with no substantive truth-vs-belief / attitude fields must
        # NOT fall through to nominal; it is an incomplete analysis.
        marker_only = classify_observation(
            {
                "injection_triggered": True,
                "injection_readback_ok": True,
                "post_injection_s": 90.0,
                "required_artifacts_present": True,
                "mechanism_evidence": True,
                "behavior_evidence": True,
            }
        )
        self.assertFalse(marker_only["accepted_observation"])
        self.assertEqual("analysis_incomplete", marker_only["behavior_class"])
        self.assertEqual("missing_behavior_fields", marker_only["reason"])

    def test_each_accepted_behavior_class_requires_its_own_evidence(self) -> None:
        base = _valid_observation()
        cases = [
            # A rejected/reset fix is not fused; drop the nominal fused flag.
            ({"fused": False, "reset_event": True}, "reset_captured"),
            ({"fused": False, "pos_test_ratio_rejected": True}, "detected_rejected"),
            ({"mode_change": True}, "autopilot_contained"),
            ({"failsafe": True}, "autopilot_contained"),
            (
                {
                    "horizontal_gap_m": 90.0,
                    "gap_growing": True,
                    "gap_within_nominal_band": False,
                },
                "silent_drift",
            ),
        ]
        for updates, expected in cases:
            with self.subTest(expected=expected):
                summary = classify_observation({**base, **updates})
                self.assertTrue(summary["accepted_observation"], summary)
                self.assertEqual(expected, summary["behavior_class"])

    def test_contradictory_and_malformed_behavior_evidence_is_rejected(self) -> None:
        base = _valid_observation()
        contradictory = classify_observation(
            {**base, "fused": True, "pos_test_ratio_rejected": True}
        )
        self.assertFalse(contradictory["accepted_observation"])
        self.assertEqual("analysis_incomplete", contradictory["behavior_class"])
        self.assertEqual("contradictory_fused_and_rejected", contradictory["reason"])

        non_bool = classify_observation({**base, "gap_growing": "yes"})
        self.assertFalse(non_bool["accepted_observation"])
        self.assertEqual("analysis_incomplete", non_bool["behavior_class"])
        self.assertEqual("invalid_behavior_field_gap_growing", non_bool["reason"])

        non_finite = classify_observation({**base, "horizontal_gap_m": math.inf})
        self.assertFalse(non_finite["accepted_observation"])
        self.assertEqual("analysis_incomplete", non_finite["behavior_class"])
        self.assertEqual("non_finite_behavior_field_horizontal_gap_m", non_finite["reason"])

        unsupported = classify_observation(
            {**base, "behavior_fields": {"made_up_behavior_flag": True}}
        )
        self.assertFalse(unsupported["accepted_observation"])
        self.assertEqual("unsupported_behavior_fields", unsupported["reason"])

    def test_missing_mechanism_evidence_is_incomplete(self) -> None:
        base = _valid_observation()
        base.pop("mechanism_evidence")
        summary = classify_observation(base)
        self.assertFalse(summary["accepted_observation"])
        self.assertEqual("analysis_incomplete", summary["behavior_class"])
        self.assertEqual("missing_mechanism_fields", summary["reason"])

    def test_analysis_incomplete_for_short_window_and_missing_artifacts(self) -> None:
        short_window = classify_observation(
            {
                "injection_triggered": True,
                "injection_readback_ok": True,
                "post_injection_s": 30.0,
                "required_artifacts_present": True,
            }
        )
        self.assertFalse(short_window["accepted_observation"])
        self.assertEqual("analysis_incomplete", short_window["behavior_class"])
        self.assertEqual(
            "insufficient_post_injection_window",
            short_window["observation_quality_class"],
        )

        missing_artifacts = classify_observation(
            {
                "injection_triggered": True,
                "injection_readback_ok": True,
                "post_injection_s": 90.0,
                "required_artifacts_present": False,
            }
        )
        self.assertFalse(missing_artifacts["accepted_observation"])
        self.assertEqual("analysis_incomplete", missing_artifacts["behavior_class"])
        self.assertEqual(
            "missing_required_artifacts",
            missing_artifacts["observation_quality_class"],
        )

        missing_mechanism = classify_observation(
            {
                "injection_triggered": True,
                "injection_readback_ok": True,
                "post_injection_s": 90.0,
                "required_artifacts_present": True,
                "behavior_evidence": True,
            }
        )
        self.assertFalse(missing_mechanism["accepted_observation"])
        self.assertEqual("analysis_incomplete", missing_mechanism["behavior_class"])
        self.assertEqual("missing_mechanism_fields", missing_mechanism["reason"])

        explicit_mechanism_false = classify_observation(
            _valid_observation(mechanism_evidence=False)
        )
        self.assertFalse(explicit_mechanism_false["accepted_observation"])
        self.assertEqual("analysis_incomplete", explicit_mechanism_false["behavior_class"])

        missing_behavior = classify_observation(
            {
                "injection_triggered": True,
                "injection_readback_ok": True,
                "post_injection_s": 90.0,
                "required_artifacts_present": True,
                "mechanism_evidence": True,
            }
        )
        self.assertFalse(missing_behavior["accepted_observation"])
        self.assertEqual("analysis_incomplete", missing_behavior["behavior_class"])
        self.assertEqual("missing_behavior_fields", missing_behavior["reason"])

        # Dropping a required substantive behavior field (attitude band) from an
        # otherwise-valid observation must fail closed as incomplete.
        partial_behavior = _valid_observation()
        partial_behavior.pop("attitude_in_band")
        partial_behavior_result = classify_observation(partial_behavior)
        self.assertFalse(partial_behavior_result["accepted_observation"])
        self.assertEqual(
            "analysis_incomplete", partial_behavior_result["behavior_class"]
        )
        self.assertEqual("missing_behavior_fields", partial_behavior_result["reason"])

        terminal_short = classify_observation(
            {
                "injection_triggered": True,
                "injection_readback_ok": True,
                "post_injection_s": 30.0,
                "terminal_state_reached": True,
                "required_artifacts_present": True,
                "mechanism_evidence": True,
                "behavior_evidence": True,
                "loss_of_control": True,
            }
        )
        self.assertFalse(terminal_short["accepted_observation"])
        self.assertEqual("analysis_incomplete", terminal_short["behavior_class"])

    def test_manifest_acceptance_fails_closed_for_contradictions(self) -> None:
        self.assertTrue(accepted_observation_from_attempt(_accepted_attempt()))
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    verdict={
                        "class": "failed_analysis",
                        "reason": "failed_analysis",
                        "metadata": {"accepted_observation": True},
                    }
                )
            )
        )
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    analysis_results=[
                        {
                            "ok": True,
                            "summary": {
                                "accepted_observation": True,
                                "behavior_class": "analysis_incomplete",
                            },
                        }
                    ]
                )
            )
        )
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(accepted_observation=True, analysis_results=[])
            )
        )
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(accepted_observation=False)
            )
        )
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(status="failed", accepted_observation=True)
            )
        )
        for terminal in ("pending", "running", "partial", "failed_analysis"):
            with self.subTest(terminal=terminal):
                self.assertFalse(
                    accepted_observation_from_attempt(
                        _accepted_attempt(status=terminal, accepted_observation=True)
                    )
                )
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    verdict={
                        "class": "success",
                        "reason": "loss_of_control",
                        "metadata": {"accepted_observation": False},
                    }
                )
            )
        )
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(verdict=None, status="success")
            )
        )
        self.assertFalse(
            accepted_observation_from_attempt(
                {
                    "analysis_results": [
                        {
                            "ok": True,
                            "summary": {
                                "accepted_observation": True,
                                "behavior_class": "loss_of_control",
                            },
                        }
                    ]
                }
            )
        )
        self.assertTrue(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    verdict={
                        "class": "success",
                        "reason": "detected_rejected",
                        "metadata": {"accepted_observation": True},
                    },
                    analysis_results=[
                        {
                            "ok": True,
                            "summary": {
                                "accepted_observation": True,
                                "behavior_class": "detected_rejected",
                                "observation_quality_class": "valid_detected_rejection",
                            },
                        }
                    ],
                )
            )
        )

    def test_manifest_requires_verdict_and_analysis_behavior_to_agree(self) -> None:
        # Headline Blocker-4 case: verdict says loss_of_control but the
        # authoritative analysis says detected_rejected -> must NOT be accepted.
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    verdict={
                        "class": "success",
                        "reason": "loss_of_control",
                        "metadata": {"accepted_observation": True},
                    },
                    analysis_results=[
                        {
                            "ok": True,
                            "summary": {
                                "accepted_observation": True,
                                "behavior_class": "detected_rejected",
                                "observation_quality_class": "valid_detected_rejection",
                            },
                        }
                    ],
                )
            )
        )
        # Multiple incompatible analysis behavior classes fail closed.
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    analysis_results=[
                        {
                            "ok": True,
                            "summary": {
                                "accepted_observation": True,
                                "behavior_class": "loss_of_control",
                            },
                        },
                        {
                            "ok": True,
                            "summary": {
                                "accepted_observation": True,
                                "behavior_class": "detected_rejected",
                            },
                        },
                    ]
                )
            )
        )
        # Unknown behavior class fails closed.
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    verdict={
                        "class": "success",
                        "reason": "made_up_class",
                        "metadata": {"accepted_observation": True},
                    },
                    analysis_results=[
                        {
                            "ok": True,
                            "summary": {
                                "accepted_observation": True,
                                "behavior_class": "made_up_class",
                            },
                        }
                    ],
                )
            )
        )
        # A missing verdict accepted-observation metadata flag fails closed even
        # when everything else agrees.
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    verdict={
                        "class": "success",
                        "reason": "loss_of_control",
                        "metadata": {},
                    }
                )
            )
        )
        # Every legitimate accepted behavior class, in agreement, is accepted.
        for behavior in (
            "nominal",
            "silent_drift",
            "detected_rejected",
            "reset_captured",
            "autopilot_contained",
            "loss_of_control",
        ):
            with self.subTest(behavior=behavior):
                self.assertTrue(
                    accepted_observation_from_attempt(
                        _accepted_attempt(
                            verdict={
                                "class": "success",
                                "reason": behavior,
                                "metadata": {"accepted_observation": True},
                            },
                            analysis_results=[
                                {
                                    "ok": True,
                                    "summary": {
                                        "accepted_observation": True,
                                        "behavior_class": behavior,
                                    },
                                }
                            ],
                        )
                    )
                )

    def test_manifest_rejects_malformed_acceptance_and_unknown_quality(self) -> None:
        # A truthy non-bool top-level accepted_observation is malformed.
        for bad in ("true", 1, "1", [True]):
            with self.subTest(top_level=bad):
                self.assertFalse(
                    accepted_observation_from_attempt(
                        _accepted_attempt(accepted_observation=bad)
                    )
                )
        # A strict True top-level flag with everything in agreement is accepted.
        self.assertTrue(
            accepted_observation_from_attempt(_accepted_attempt(accepted_observation=True))
        )
        # An unknown observation-quality class fails closed even with agreeing
        # behavior classes.
        self.assertFalse(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    analysis_results=[
                        {
                            "ok": True,
                            "summary": {
                                "accepted_observation": True,
                                "behavior_class": "loss_of_control",
                                "observation_quality_class": "unknown_quality",
                            },
                        }
                    ]
                )
            )
        )
        # A known-good quality class is accepted.
        self.assertTrue(
            accepted_observation_from_attempt(
                _accepted_attempt(
                    analysis_results=[
                        {
                            "ok": True,
                            "summary": {
                                "accepted_observation": True,
                                "behavior_class": "loss_of_control",
                                "observation_quality_class": "valid_bad_behavior",
                            },
                        }
                    ]
                )
            )
        )

    def test_config_rejects_invalid_ladders_and_repeat_contracts(self) -> None:
        with self.assertRaisesRegex(ValueError, "jamming_repeats must be >= 5"):
            GpsFailureConfig(jamming_repeats=1)

        with self.assertRaisesRegex(ValueError, "drift_rates_mps must not be empty"):
            GpsFailureConfig(drift_rates_mps=())
        with self.assertRaisesRegex(ValueError, "glitch_magnitudes_m must not be empty"):
            GpsFailureConfig(glitch_magnitudes_m=())
        with self.assertRaisesRegex(ValueError, "denial_durations_s must not be empty"):
            GpsFailureConfig(denial_durations_s=())

        with self.assertRaisesRegex(ValueError, "drift_rates_mps contains duplicate"):
            GpsFailureConfig(drift_rates_mps=(0.2, 0.20))
        with self.assertRaisesRegex(ValueError, "glitch_magnitudes_m contains duplicate"):
            GpsFailureConfig(glitch_magnitudes_m=(10, 10.0))
        with self.assertRaisesRegex(ValueError, "denial_durations_s contains duplicate"):
            GpsFailureConfig(denial_durations_s=(5, 5.0))

        with self.assertRaisesRegex(ValueError, "drift_rates_mps value must be finite"):
            GpsFailureConfig(drift_rates_mps=(math.nan,))
        with self.assertRaisesRegex(ValueError, "drift_rates_mps value must be finite"):
            GpsFailureConfig(drift_rates_mps=(math.inf,))
        with self.assertRaisesRegex(ValueError, "glitch_magnitudes_m value must be finite"):
            GpsFailureConfig(glitch_magnitudes_m=(math.nan,))
        with self.assertRaisesRegex(ValueError, "denial_durations_s value must be finite"):
            GpsFailureConfig(denial_durations_s=(math.inf,))

        with self.assertRaisesRegex(ValueError, "drift_rates_mps value must be > 0"):
            GpsFailureConfig(drift_rates_mps=(0.0,))
        with self.assertRaisesRegex(ValueError, "glitch_magnitudes_m value must be > 0"):
            GpsFailureConfig(glitch_magnitudes_m=(-1.0,))
        with self.assertRaisesRegex(ValueError, "denial_durations_s value must be > 0"):
            GpsFailureConfig(denial_durations_s=(0.0,))

    def test_custom_drift_values_generate_distinct_collision_free_ids(self) -> None:
        cases = _cases(GpsFailureConfig(drift_rates_mps=(0.21, 0.24)))
        case_ids = [case.case_id for case in cases]
        self.assertIn("slow_drift_0p21_mps", case_ids)
        self.assertIn("slow_drift_0p24_mps", case_ids)
        self.assertEqual(len(case_ids), len(set(case_ids)))

    def test_readback_comparison_rejects_non_finite_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected must be finite"):
            compare_readback({"SIM_GPS1_ENABLE": math.nan}, {"SIM_GPS1_ENABLE": 1.0})
        with self.assertRaisesRegex(ValueError, "actual must be finite"):
            compare_readback({"SIM_GPS1_ENABLE": 1.0}, {"SIM_GPS1_ENABLE": math.nan})

    def test_case_and_schema_metadata_are_isolated(self) -> None:
        first, second = _cases()[:2]
        first.parameters["parameter_metadata"]["SIM_GPS1_ENABLE"]["units"] = "mutated"
        self.assertEqual(
            "enum 0/1",
            second.parameters["parameter_metadata"]["SIM_GPS1_ENABLE"]["units"],
        )
        schema = defaults.parameter_schema()
        schema["metadata"]["SIM_GPS1_ENABLE"]["units"] = "schema_mutated"
        fresh = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("nominal")
        self.assertEqual(
            "enum 0/1",
            fresh.parameters["parameter_metadata"]["SIM_GPS1_ENABLE"]["units"],
        )
        self.assertEqual("enum 0/1", defaults.PARAMETER_METADATA["SIM_GPS1_ENABLE"]["units"])

    def test_cli_invalid_case_fails_before_launch(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure",
                "--dry-run",
                "--case",
                "does_not_exist",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("Unknown gps_failure case id", proc.stderr)
        self.assertNotIn("launch", proc.stdout.lower())

    def test_no_legacy_wind_runner_tokens_in_gps_plugin_sources(self) -> None:
        plugin_dir = SRC / "sim_ard_gaw/campaigns/test_suite/plugins/gps_failure"
        forbidden = ("run_one", "run_matrix", "run_matrix_round_robin")
        for path in plugin_dir.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, text)

    def test_no_legacy_runner_imports_during_plugin_construction(self) -> None:
        blocked = {
            "sim_ard_gaw.campaigns.wind_matrix.run_one",
            "sim_ard_gaw.campaigns.wind_matrix.run_matrix",
            "sim_ard_gaw.campaigns.wind_matrix.run_matrix_round_robin",
            "run_one",
            "run_matrix",
            "run_matrix_round_robin",
        }

        class BlockLegacy(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname in blocked:
                    raise AssertionError(f"blocked legacy runner import: {fullname}")
                return None

        finder = BlockLegacy()
        sys.meta_path.insert(0, finder)
        try:
            plugin = build_plugin(GpsFailureConfig(launch_stack=False))
            list(plugin.case_generator.iter_cases())
            plugin.attempt_runner()
        finally:
            sys.meta_path.remove(finder)


if __name__ == "__main__":
    unittest.main()
