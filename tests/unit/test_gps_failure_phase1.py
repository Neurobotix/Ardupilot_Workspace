from __future__ import annotations

import importlib.abc
import json
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
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.case_generator import (  # noqa: E402
    GpsFailureCaseGenerator,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.config import (  # noqa: E402
    GpsFailureConfig,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.manifest import (  # noqa: E402
    GpsFailureManifest,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.monitor import (  # noqa: E402
    first_seq4_edge_after_armed_auto_front_half,
    first_seq4_edge_after_front_half,
    trigger_metadata,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.plugin import (  # noqa: E402
    build_plugin,
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


def _cases(config: GpsFailureConfig | None = None):
    return list(GpsFailureCaseGenerator(config or GpsFailureConfig()).iter_cases())


class GpsFailurePhase1Tests(unittest.TestCase):
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
        self.assertEqual("hard_denial", data["case"]["parameters"]["fault_type"])

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
        self.assertIn("plane_gps.parm", schema["planned_param_stack"][1])
        self.assertEqual(1, len(schema["phase1_param_stack"]))
        defaults.validate_required_param_names(schema["required_names"])
        with self.assertRaisesRegex(ValueError, "Missing required"):
            defaults.validate_required_param_names(["SIM_GPS1_ENABLE"])

        for case in _cases():
            self.assertEqual(EXPECTED_SOURCE_DEFAULTS, case.parameters["reset_payload"])

        self.assertEqual(90.0, defaults.MIN_POST_INJECTION_S)
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
            {"seq": 2, "armed": True, "mode": "AUTO"},
            {"seq": 3, "armed": True, "mode": "AUTO"},
            {"seq": 4, "armed": True, "mode": "AUTO"},
        ]
        self.assertTrue(first_seq4_edge_after_armed_auto_front_half(good))
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

    def test_artifact_schema_uses_locked_gps_names(self) -> None:
        schemas = artifact_schema()
        self.assertIn("gps_behavior_summary.json", schemas)
        self.assertIn("ekf_innovation_metrics.json", schemas)
        self.assertIn("truth_vs_belief.json", schemas)
        self.assertIn("mode_timeline.json", schemas)
        self.assertIn("attitude_altitude_envelope.json", schemas)
        self.assertNotIn("gps_signal_metrics.json", schemas)
        self.assertNotIn("altitude_envelope.json", schemas)

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
        base = {
            "injection_triggered": True,
            "injection_readback_ok": True,
            "post_injection_s": 90.0,
            "required_artifacts_present": True,
        }
        result = classify_observation({**base, "loss_of_control": True})
        self.assertTrue(result["accepted_observation"])
        self.assertEqual("loss_of_control", result["behavior_class"])
        silent = classify_observation(
            {
                **base,
                "fused": True,
                "truth_belief_gap_growing": True,
                "failsafe": False,
            }
        )
        self.assertTrue(silent["accepted_observation"])
        self.assertEqual("silent_drift", silent["behavior_class"])

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

        missing_fields = classify_observation(
            {
                "injection_triggered": True,
                "injection_readback_ok": True,
                "post_injection_s": 90.0,
                "required_artifacts_present": True,
                "mechanism_fields_present": False,
            }
        )
        self.assertFalse(missing_fields["accepted_observation"])
        self.assertEqual("analysis_incomplete", missing_fields["behavior_class"])

        terminal_short = classify_observation(
            {
                "injection_triggered": True,
                "injection_readback_ok": True,
                "post_injection_s": 30.0,
                "terminal_state_reached": True,
                "required_artifacts_present": True,
                "loss_of_control": True,
            }
        )
        self.assertFalse(terminal_short["accepted_observation"])
        self.assertEqual("analysis_incomplete", terminal_short["behavior_class"])

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
