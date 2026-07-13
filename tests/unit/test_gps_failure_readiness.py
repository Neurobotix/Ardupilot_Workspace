"""Phase-1 Chunk 6 integration-readiness tests for the gps_failure lane.

These are no-SITL tests. They prove the GPS lane is wired into the shared suite
path far enough to run and that the readiness report faithfully reports the
Phase-1 no-SITL posture and the live blockers. Nothing here launches SITL or
opens a MAVLink connection.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.campaigns.test_suite.cli._registry import PLUGINS  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure import defaults  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.config import (  # noqa: E402
    GpsFailureConfig,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.plugin import (  # noqa: E402
    GpsFailurePlugin,
    build_plugin,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.readiness import (  # noqa: E402
    LIVE_BLOCKERS,
    build_readiness_report,
)


class ReadinessReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = build_readiness_report()

    def test_report_is_phase1_no_sitl_and_not_live_ready(self) -> None:
        self.assertEqual(self.report["phase"], "phase1_no_sitl")
        self.assertFalse(self.report["launch_stack"])
        self.assertFalse(self.report["launch_performed"])
        self.assertFalse(self.report["live_readback_performed"])
        self.assertFalse(self.report["ready_for_live_run"])

    def test_suite_path_exposes_every_suiterunner_seam(self) -> None:
        suite = self.report["suite_path"]
        self.assertEqual(suite["registry_key"], defaults.SUITE_NAME)
        self.assertTrue(suite["attempt_runner_built"])
        self.assertTrue(suite["attempt_dir_factory_built"])
        self.assertEqual(suite["case_generator"], "GpsFailureCaseGenerator")
        self.assertEqual(suite["manifest"], "GpsFailureManifest")
        self.assertTrue(suite["all_cases_share_mission"])

    def test_scheduled_case_count_matches_full_catalog(self) -> None:
        plugin = build_plugin()
        expected_ids = [case.case_id for case in plugin.case_generator.iter_cases()]
        suite = self.report["suite_path"]
        self.assertEqual(suite["scheduled_case_count"], len(expected_ids))
        self.assertEqual(suite["scheduled_case_ids"], expected_ids)
        # nominal + 6 drift rates + accumulation + 6 glitch + 4 denial + 5 jam
        self.assertEqual(suite["scheduled_case_count"], 23)

    def test_case_catalog_counts_by_fault_type(self) -> None:
        by_fault = self.report["case_catalog"]["by_fault_type"]
        self.assertEqual(by_fault["nominal"], 1)
        self.assertEqual(by_fault["slow_drift"], 7)
        self.assertEqual(by_fault["step_glitch"], 6)
        self.assertEqual(by_fault["hard_denial"], 4)
        self.assertEqual(by_fault["jamming"], 5)
        self.assertEqual(sum(by_fault.values()), self.report["case_catalog"]["total"])

    def test_manifest_contract_is_empty_and_disk_untouched(self) -> None:
        contract = self.report["manifest_contract"]
        self.assertEqual(contract["adapter"], "GpsFailureManifest")
        self.assertTrue(contract["attempts_initially_empty"])
        self.assertIn("attempts", contract["top_level_keys"])
        # Building the report must never write a manifest file.
        self.assertFalse(
            (build_plugin().config.campaign_root / "manifest.json").exists()
        )

    def test_artifact_contract_matches_locked_names(self) -> None:
        contract = self.report["artifact_contract"]
        self.assertEqual(
            contract["required_attempt_artifacts"],
            list(defaults.REQUIRED_ATTEMPT_ARTIFACTS),
        )
        self.assertEqual(contract["min_post_injection_s"], defaults.MIN_POST_INJECTION_S)
        self.assertIn("gps_behavior_summary.json", contract["artifact_schema"])

    def test_readiness_exposes_complete_schema_including_gps_injection(self) -> None:
        contract = self.report["artifact_contract"]
        # The historical gap: gps_injection.json is required and must now have a
        # schema entry, and readiness must report full coverage.
        self.assertIn("gps_injection.json", contract["artifact_schema"])
        self.assertIn("gps_injection.json", contract["artifact_schema_names"])
        self.assertEqual([], contract["required_artifacts_without_schema"])
        self.assertTrue(contract["schema_covers_required_artifacts"])
        for name in defaults.REQUIRED_ATTEMPT_ARTIFACTS:
            self.assertIn(name, contract["artifact_schema"], name)

    def test_parameter_stack_is_the_two_file_phase1_stack(self) -> None:
        stack = self.report["parameter_stack"]["effective_param_stack"]
        self.assertEqual(len(stack), 2)
        self.assertTrue(stack[0].endswith("plane_base.parm"))
        self.assertTrue(stack[1].endswith("plane_gps.parm"))

    def test_live_blockers_cover_the_three_live_adapters(self) -> None:
        blockers = self.report["live_blockers"]
        components = {item["component"] for item in blockers}
        self.assertIn("environment.GpsFailureEnvironment", components)
        self.assertIn("control.GpsFailureMissionControl", components)
        self.assertIn("monitor.GpsFailureMonitor", components)
        self.assertEqual(len(blockers), len(LIVE_BLOCKERS))

    def test_report_built_from_registry_plugin_is_consistent(self) -> None:
        registry_plugin = cast(GpsFailurePlugin, PLUGINS["gps_failure"]())
        registry_report = build_readiness_report(registry_plugin)
        self.assertEqual(
            registry_report["suite_path"]["scheduled_case_ids"],
            self.report["suite_path"]["scheduled_case_ids"],
        )

    def test_report_reflects_a_narrowed_case_config(self) -> None:
        config = GpsFailureConfig(
            drift_rates_mps=(0.5,),
            glitch_magnitudes_m=(50,),
            denial_durations_s=(30,),
        )
        report = build_readiness_report(build_plugin(config))
        by_fault = report["case_catalog"]["by_fault_type"]
        self.assertEqual(by_fault["slow_drift"], 2)  # one rate + accumulation
        self.assertEqual(by_fault["step_glitch"], 1)
        self.assertEqual(by_fault["hard_denial"], 1)

    def test_report_is_json_serializable_without_nan(self) -> None:
        # allow_nan=False raises on any non-finite value leaking into the report.
        dumped = json.dumps(self.report, allow_nan=False, sort_keys=True)
        self.assertIn("phase1_no_sitl", dumped)


class ReadinessCliTests(unittest.TestCase):
    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure",
                *args,
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
        )

    def test_preflight_emits_valid_readiness_json(self) -> None:
        result = self._run_cli("--preflight")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["phase"], "phase1_no_sitl")
        self.assertFalse(report["ready_for_live_run"])
        self.assertEqual(report["suite_path"]["registry_key"], "gps_failure")

    def test_preflight_is_mutually_exclusive_with_other_actions(self) -> None:
        result = self._run_cli("--preflight", "--list-cases")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed with", result.stderr)


if __name__ == "__main__":
    unittest.main()
