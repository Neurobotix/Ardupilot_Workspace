from __future__ import annotations

import importlib.abc
import json
import os
import subprocess
import sys
import tempfile
import textwrap
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
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure import defaults  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.analyzers import (  # noqa: E402
    artifact_schema,
    classify_observation,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.case_generator import (  # noqa: E402
    AirspeedFailureCaseGenerator,
    ratio_case_id,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.config import (  # noqa: E402
    AirspeedFailureConfig,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.environment import (  # noqa: E402
    build_reference_wind_artifact,
    reference_wind_artifact_schema,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.manifest import (  # noqa: E402
    AirspeedFailureManifest,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.monitor import (  # noqa: E402
    first_seq4_edge_after_front_half,
    trigger_metadata,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.plugin import (  # noqa: E402
    build_plugin,
)
from sim_ard_gaw.campaigns.test_suite.plugins.airspeed_failure.stimulus import (  # noqa: E402
    build_injection_artifact,
    compare_readback,
)

EXPECTED_SIM_ARSPD_PARAMS = [
    "SIM_ARSPD_RND",
    "SIM_ARSPD_OFS",
    "SIM_ARSPD_FAIL",
    "SIM_ARSPD_FAILP",
    "SIM_ARSPD_PITOT",
    "SIM_ARSPD_SIGN",
    "SIM_ARSPD_RATIO",
]

EXPECTED_SOURCE_DEFAULTS = {
    "SIM_ARSPD_RND": 2.0,
    "SIM_ARSPD_OFS": 2013.0,
    "SIM_ARSPD_FAIL": 0.0,
    "SIM_ARSPD_FAILP": 0.0,
    "SIM_ARSPD_PITOT": 0.0,
    "SIM_ARSPD_SIGN": 0.0,
    "SIM_ARSPD_RATIO": 1.99,
}


def _cases(config: AirspeedFailureConfig | None = None):
    return list(AirspeedFailureCaseGenerator(config or AirspeedFailureConfig()).iter_cases())


class AirspeedFailurePhase1Tests(unittest.TestCase):
    def test_fixed_case_generation_payloads(self) -> None:
        cases = _cases()
        self.assertEqual(
            [
                "healthy_reference",
                "noise_5",
                "noise_10",
                "pitot_500pa",
                "fail_primary",
                "sign_reversed",
            ],
            [case.case_id for case in cases[:6]],
        )
        payloads = {case.case_id: case.parameters["injection_payload"] for case in cases}
        self.assertEqual({}, payloads["healthy_reference"])
        self.assertEqual({"SIM_ARSPD_RND": 5.0}, payloads["noise_5"])
        self.assertEqual({"SIM_ARSPD_RND": 10.0}, payloads["noise_10"])
        self.assertEqual({"SIM_ARSPD_FAILP": 500.0}, payloads["pitot_500pa"])
        self.assertEqual({"SIM_ARSPD_FAIL": 1.0}, payloads["fail_primary"])
        self.assertEqual({"SIM_ARSPD_SIGN": 1.0}, payloads["sign_reversed"])

    def test_ratio_recipe_names_order_and_computation(self) -> None:
        cfg = AirspeedFailureConfig(
            ratio_bias_percents=(10, 30, 50, -10, -30, -50),
            vehicle_arspd_ratio=3.2,
            vehicle_arspd_ratio_verified=True,
        )
        ratio_cases = _cases(cfg)[6:]
        self.assertEqual(
            [
                "ratio_bias_p10",
                "ratio_bias_p30",
                "ratio_bias_p50",
                "ratio_bias_m10",
                "ratio_bias_m30",
                "ratio_bias_m50",
            ],
            [case.case_id for case in ratio_cases],
        )
        for case, bias in zip(ratio_cases, cfg.ratio_bias_percents):
            k = 1 + bias / 100
            self.assertEqual(ratio_case_id(bias), case.case_id)
            self.assertAlmostEqual(
                3.2 / (k * k),
                case.parameters["injection_payload"]["SIM_ARSPD_RATIO"],
            )
            self.assertFalse(case.parameters["calibration_required"])
            self.assertEqual(bias, case.parameters["ratio_recipe"]["bias_percent"])

    def test_ratio_calibration_required_by_default_and_floor_guard(self) -> None:
        ratio_case = _cases()[6]
        self.assertTrue(ratio_case.parameters["calibration_required"])
        self.assertEqual(2.0, ratio_case.parameters["ratio_recipe"]["vehicle_arspd_ratio"])
        with self.assertRaisesRegex(ValueError, "low-side floor"):
            AirspeedFailureConfig(ratio_bias_percents=(-80,))
        with self.assertRaisesRegex(ValueError, "non-zero"):
            AirspeedFailureConfig(ratio_bias_percents=(0,))

    def test_invalid_case_id_rejected_before_launch(self) -> None:
        generator = AirspeedFailureCaseGenerator(AirspeedFailureConfig())
        with self.assertRaisesRegex(ValueError, "Unknown airspeed_failure case id"):
            generator.get_case("missing_case")

    def test_parameter_schema_validation_and_payload_semantics(self) -> None:
        schema = defaults.parameter_schema()
        self.assertEqual(EXPECTED_SIM_ARSPD_PARAMS, list(defaults.REQUIRED_SIM_ARSPD_PARAMS))
        self.assertEqual(EXPECTED_SIM_ARSPD_PARAMS, schema["required_names"])
        self.assertEqual(EXPECTED_SOURCE_DEFAULTS, defaults.SOURCE_DEFAULTS)
        self.assertEqual(EXPECTED_SOURCE_DEFAULTS, schema["source_defaults"])
        defaults.validate_required_param_names(schema["required_names"])
        with self.assertRaisesRegex(ValueError, "Missing required"):
            defaults.validate_required_param_names(["SIM_ARSPD_FAIL"])

        cases = {case.case_id: case for case in _cases()}
        for case in cases.values():
            self.assertEqual(EXPECTED_SOURCE_DEFAULTS, case.parameters["reset_payload"])
            self.assertEqual(1.99, case.parameters["reset_payload"]["SIM_ARSPD_RATIO"])

        self.assertEqual(
            {"SIM_ARSPD_FAIL": 1.0},
            cases["fail_primary"].parameters["injection_payload"],
        )
        self.assertEqual(
            {"SIM_ARSPD_FAILP": 500.0},
            cases["pitot_500pa"].parameters["injection_payload"],
        )
        active_payload_names = {
            name
            for case in cases.values()
            for name in case.parameters["injection_payload"]
        }
        self.assertNotIn("SIM_ARSPD_OFS", active_payload_names)
        self.assertNotEqual(
            {"SIM_ARSPD_PITOT": 500.0},
            cases["pitot_500pa"].parameters["injection_payload"],
        )

    def test_trigger_metadata_and_readback_shape(self) -> None:
        meta = trigger_metadata()
        self.assertEqual("MISSION_CURRENT", meta["source"])
        self.assertEqual(4, meta["seq"])
        self.assertEqual("first seq==4 after front-half progress", meta["edge"])
        self.assertTrue(first_seq4_edge_after_front_half([1, 2, 3, 4]))
        self.assertFalse(first_seq4_edge_after_front_half([4]))

        case = AirspeedFailureCaseGenerator(AirspeedFailureConfig()).get_case("fail_primary")
        artifact = build_injection_artifact(case)
        self.assertEqual({"SIM_ARSPD_FAIL": 1.0}, artifact["requested_payload"])
        self.assertEqual("pending_phase2", artifact["readback_status_shape"]["injection"])
        self.assertTrue(compare_readback({"SIM_ARSPD_FAIL": 1.0}, {"SIM_ARSPD_FAIL": 1.0})["ok"])
        self.assertFalse(compare_readback({"SIM_ARSPD_FAIL": 1.0}, {"SIM_ARSPD_FAIL": 2.0})["ok"])

    def test_reference_wind_and_analysis_artifact_schemas(self) -> None:
        wind = build_reference_wind_artifact()
        self.assertEqual({"x": -5.0, "y": 0.0, "z": 0.0}, wind["requested_mps"])
        self.assertEqual("before_mission_start", wind["publication_timing"])
        self.assertEqual("gz_topic_publish", wind["method"])
        self.assertIsNone(wind["echo_parsed_mps"])
        self.assertIsNone(wind["realized_arsp_minus_gps_eastbound_mps"])
        self.assertEqual("pending_phase2", wind["sign_confirmation"]["status"])
        self.assertEqual(defaults.WIND_TOPIC, wind["topic"])
        self.assertFalse(wind["verified"])
        fields = cast(list[str], reference_wind_artifact_schema()["required_fields"])
        for field in (
            "requested_mps",
            "publication_timing",
            "method",
            "echo_parsed_mps",
            "realized_arsp_minus_gps_eastbound_mps",
            "sign_confirmation",
        ):
            self.assertIn(field, fields)

        schemas = artifact_schema()
        self.assertIn("airspeed_behavior_summary.json", schemas)
        self.assertIn("airspeed_signal_metrics.json", schemas)
        self.assertIn("mission_progress.json", schemas)
        self.assertIn("mode_timeline.json", schemas)
        self.assertIn("altitude_speed_envelope.json", schemas)
        self.assertTrue(schemas["tecs_response.json"]["optional"])

    def test_default_campaign_root_is_timestamped_under_var_runs(self) -> None:
        cfg = AirspeedFailureConfig()
        self.assertEqual(defaults.DEFAULT_CAMPAIGN_ROOT_PARENT, cfg.campaign_root.parent)
        self.assertRegex(
            cfg.campaign_root.name,
            r"^airspeed_failure_behavior_\d{8}T\d{12}Z$",
        )

    def test_behavior_classification_and_planned_rtl_discriminator(self) -> None:
        base = {
            "injection_triggered": True,
            "injection_readback_ok": True,
            "wind_verified": True,
            "post_injection_s": 30,
            "required_artifacts_present": True,
            "mission_complete": True,
        }
        self.assertEqual(
            "nominal_completion",
            classify_observation(base)["behavior_class"],
        )
        self.assertEqual(
            "degraded_completion",
            classify_observation({**base, "altitude_loss_m": 31})["behavior_class"],
        )
        self.assertEqual(
            "autopilot_contained",
            classify_observation(
                {**base, "mission_complete": False, "auto_to_rtl_transition_seq": 5}
            )["behavior_class"],
        )
        self.assertEqual(
            "nominal_completion",
            classify_observation({**base, "auto_to_rtl_transition_seq": 8})[
                "behavior_class"
            ],
        )
        self.assertEqual(
            "loss_of_control_or_timeout",
            classify_observation({**base, "timeout": True})["behavior_class"],
        )

    def test_observation_quality_gates_bad_flights_only_after_valid_injection(self) -> None:
        valid_bad = classify_observation(
            {
                "injection_triggered": True,
                "injection_readback_ok": True,
                "wind_verified": True,
                "terminal_state_reached": True,
                "required_artifacts_present": True,
                "loss_of_control": True,
            }
        )
        self.assertTrue(valid_bad["accepted_observation"])
        self.assertEqual("loss_of_control_or_timeout", valid_bad["behavior_class"])

        for obs, quality in (
            ({"launch_failed": True}, "failed_launch"),
            ({"injection_triggered": False}, "pre_injection"),
            (
                {"injection_triggered": True, "injection_readback_ok": False},
                "failed_readback",
            ),
            (
                {
                    "injection_triggered": True,
                    "injection_readback_ok": True,
                    "wind_verified": False,
                },
                "unverified_wind",
            ),
            (
                {
                    "injection_triggered": True,
                    "injection_readback_ok": True,
                    "wind_verified": True,
                    "post_injection_s": 5,
                },
                "insufficient_post_injection_window",
            ),
        ):
            with self.subTest(quality=quality):
                result = classify_observation(obs)
                self.assertFalse(result["accepted_observation"])
                self.assertEqual(quality, result["observation_quality_class"])

    def test_manifest_accepted_count_uses_valid_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = AirspeedFailureManifest(root)
            case = AirspeedFailureCaseGenerator(AirspeedFailureConfig()).get_case(
                "fail_primary"
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
                    reason="loss_of_control_or_timeout",
                    retryable=False,
                    metadata={"accepted_observation": True},
                ),
                analysis_results=[
                    AnalysisResult(
                        analyzer_name="airspeed",
                        ok=True,
                        summary={
                            "accepted_observation": True,
                            "behavior_class": "loss_of_control_or_timeout",
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
                    reason="analysis_incomplete",
                    retryable=True,
                    metadata={"accepted_observation": False},
                ),
            )
            manifest.append_attempt(accepted)
            manifest.append_attempt(rejected)
            self.assertEqual(1, manifest.accepted_count(case))

    def test_plugin_registry_and_construction_without_legacy_runner_imports(self) -> None:
        self.assertIn("airspeed_failure", PLUGINS)
        plugin = cast(Any, PLUGINS["airspeed_failure"](launch_stack=False))
        self.assertEqual(
            defaults.SUITE_NAME,
            next(iter(plugin.case_generator.iter_cases())).suite_name,
        )

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
            plugin = build_plugin(AirspeedFailureConfig(launch_stack=False))
            list(plugin.case_generator.iter_cases())
            plugin.attempt_runner()
        finally:
            sys.meta_path.remove(finder)

    def test_cli_list_cases_and_dry_run(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        list_proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure",
                "--list-cases",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("healthy_reference", list_proc.stdout.splitlines())
        self.assertIn("ratio_bias_p30", list_proc.stdout.splitlines())

        dry_proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure",
                "--dry-run",
                "--case",
                "ratio_bias_p30",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        data = json.loads(dry_proc.stdout)
        self.assertTrue(data["plugin_constructed"])
        self.assertFalse(data["launch_performed"])
        self.assertTrue(data["case"]["parameters"]["calibration_required"])
        self.assertEqual(
            "SIM_ARSPD_RATIO = ARSPD_RATIO / k^2",
            data["case"]["parameters"]["ratio_recipe"]["formula"],
        )

    def test_cli_invalid_case_fails_before_launch(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure",
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
        self.assertIn("Unknown airspeed_failure case id", proc.stderr)

    def test_no_legacy_runner_tokens_in_airspeed_plugin_sources(self) -> None:
        plugin_dir = SRC / "sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure"
        forbidden = ("run_one", "run_matrix", "run_matrix_round_robin")
        for path in plugin_dir.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
