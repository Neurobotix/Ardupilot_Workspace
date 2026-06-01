from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class Phase3CZeroLegacyFoundationTests(unittest.TestCase):
    def test_core_has_no_wind_matrix_foundation_semantics(self) -> None:
        core_paths = sorted(
            (
                ROOT
                / "src"
                / "sim_ard_gaw"
                / "campaigns"
                / "test_suite"
                / "core"
            ).glob("*.py")
        )
        forbidden = [
            "wind_matrix",
            "run_one",
            "run_matrix",
            "success_full",
            "success_square_only",
            "wind_x_mps",
            "y_wind_mps",
            "x_wind_mps",
            "square_completed",
            "loiter_completed",
            "wind_monitor_state",
            "legacy_run_analysis",
            "combo_key",
        ]

        for path in core_paths:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, text)

    def test_core_staged_strategy_uses_framework_verdict_not_plugin_status(self) -> None:
        from sim_ard_gaw.campaigns.test_suite.core.attempt_runner import StagedStrategy
        from sim_ard_gaw.campaigns.test_suite.core.analysis import AnalyzerChain
        from sim_ard_gaw.campaigns.test_suite.core.control import ControlStrategy
        from sim_ard_gaw.campaigns.test_suite.core.environment import EnvironmentAdapter
        from sim_ard_gaw.campaigns.test_suite.core.models import (
            AnalysisResult,
            AttemptContext,
            AttemptStatus,
            MonitorResult,
            TestCase,
            Verdict,
            VerdictClass,
        )
        from sim_ard_gaw.campaigns.test_suite.core.monitor import CompletionMonitor
        from sim_ard_gaw.campaigns.test_suite.core.stimulus import StimulusAdapter
        from sim_ard_gaw.campaigns.test_suite.core.verdicts import VerdictPolicy

        class Stimulus(StimulusAdapter):
            def apply(self, case: TestCase, ctx: AttemptContext) -> dict:
                return {}

            def verify(self, case: TestCase, ctx: AttemptContext) -> dict:
                return {}

        class Control(ControlStrategy):
            def execute(self, case: TestCase, ctx: AttemptContext) -> None:
                return None

        class Monitor(CompletionMonitor):
            def run(self, case: TestCase, ctx: AttemptContext) -> MonitorResult:
                return MonitorResult(completed=False, reason="forced_failure", duration_s=0.0)

        class Verdicts(VerdictPolicy):
            def classify(
                self,
                case: TestCase,
                monitor_result: MonitorResult,
                analysis_results: Sequence[AnalysisResult],
            ) -> Verdict:
                return Verdict(VerdictClass.FAILED, "framework_verdict", True)

        case = TestCase("generic_suite", "case_001")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ctx = AttemptContext(
                case=case,
                campaign_root=root,
                attempt_dir=root / "attempt",
                attempt_index=1,
                target_run_index=1,
                start_wall_s=0.0,
                start_monotonic_s=0.0,
            )
            ctx.extra["plugin_manifest_fields"] = {
                "attempt_id": "case_001__attempt_001",
                "status": "success_full",
            }
            record = StagedStrategy(
                stimulus=Stimulus(),
                control=Control(),
                monitor=Monitor(),
                analyzers=AnalyzerChain([]),
                verdict_policy=Verdicts(),
            ).execute(ctx)

        self.assertEqual(AttemptStatus.FAILED, record.status)

    def test_staged_foundation_constructs_with_legacy_runner_imports_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            code = textwrap.dedent(
                f"""
                import importlib.abc
                import contextlib
                import io
                import json
                import sys
                from pathlib import Path
                from unittest import mock

                blocked = {{
                    "sim_ard_gaw.campaigns.wind_matrix.run_one",
                    "sim_ard_gaw.campaigns.wind_matrix.run_matrix",
                    "sim_ard_gaw.campaigns.wind_matrix.run_matrix_round_robin",
                    "run_one",
                    "run_matrix",
                    "run_matrix_round_robin",
                }}

                for name in list(sys.modules):
                    if name in blocked:
                        sys.modules.pop(name, None)

                class BlockLegacy(importlib.abc.MetaPathFinder):
                    def find_spec(self, fullname, path=None, target=None):
                        if fullname in blocked:
                            raise AssertionError(f"blocked legacy runner import: {{fullname}}")
                        return None

                sys.meta_path.insert(0, BlockLegacy())

                from sim_ard_gaw.campaigns.test_suite.cli import run_case, run_round_robin, run_suite
                from sim_ard_gaw.campaigns.test_suite.core.attempt_runner import LegacyDelegateStrategy, StagedStrategy
                from sim_ard_gaw.campaigns.test_suite.core.models import AttemptContext, AttemptRecord, AttemptStatus, TestCase, Verdict, VerdictClass
                from sim_ard_gaw.campaigns.test_suite.core.suite_runner import SuiteRunner
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.case_generator import WindMatrixCaseGenerator
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.config import WindMatrixConfig
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import analysis_helpers
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import analyzers as wind_analyzers
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import defaults
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.defaults import combo_key, DEFAULT_STAGED_AUTO_WIND_PHASE
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.manifest import WindMatrixManifest
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.analyzers import WindMatrixAnalyzer
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.plugin import build_plugin
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.stimulus import WindMatrixStimulus

                root = Path({temp_dir!r})
                default_staged_cfg = WindMatrixConfig(
                    campaign_root=root,
                    x_values=(0,),
                    y_values=(4,),
                    launch_stack=False,
                    attempt_strategy="staged",
                )
                assert default_staged_cfg.auto_control is True
                assert default_staged_cfg.auto_wind_phase == DEFAULT_STAGED_AUTO_WIND_PHASE
                default_staged_plugin = build_plugin(default_staged_cfg)
                assert isinstance(default_staged_plugin.attempt_runner()._strategy, StagedStrategy)

                cfg = WindMatrixConfig(
                    campaign_root=root,
                    x_values=(0,),
                    y_values=(4,),
                    auto_control=False,
                    launch_stack=False,
                    attempt_strategy="staged",
                )
                assert cfg.attempt_strategy == "staged"
                assert WindMatrixConfig().attempt_strategy == "legacy"

                cases = list(WindMatrixCaseGenerator(cfg).iter_cases())
                assert [case.case_id for case in cases] == ["wind_x_00_y_04"]
                assert combo_key(0, 4) == "wind_x_00_y_04"

                stimulus_ctx = AttemptContext(
                    case=cases[0],
                    campaign_root=root,
                    attempt_dir=defaults.attempt_dir(root, cases[0].case_id, 1),
                    attempt_index=1,
                    target_run_index=1,
                    start_wall_s=0.0,
                    start_monotonic_s=0.0,
                )
                stimulus = WindMatrixStimulus(cfg)
                with mock.patch.object(
                    defaults,
                    "gazebo_plugin_diagnostics",
                    return_value={{"policy": "test"}},
                ):
                    stimulus._ensure_attempt_dir(stimulus_ctx)
                    stimulus._write_run_config(cases[0], stimulus_ctx)
                run_config = json.loads(
                    (stimulus_ctx.attempt_dir / "run_config.json").read_text()
                )
                assert run_config["attempt_id"] == "wind_x_00_y_04__rep_01__attempt_001"
                assert run_config["world_name"] == defaults.WORLD_NAME
                assert run_config["wind_topic"] == defaults.WIND_TOPIC
                assert run_config["sitl_launch_command"] == defaults.CTE_SITL_COMMAND
                assert run_config["gazebo_launch_command"] == defaults.CTE_GAZEBO_COMMAND
                assert (
                    run_config["wind_injection_source"]
                    == "run_one.py via Gazebo wind topic before user mission control"
                )

                analysis_ctx = AttemptContext(
                    case=cases[0],
                    campaign_root=root,
                    attempt_dir=defaults.attempt_dir(root, cases[0].case_id, 1),
                    attempt_index=1,
                    target_run_index=1,
                    start_wall_s=0.0,
                    start_monotonic_s=0.0,
                )
                analysis_ctx.attempt_dir.mkdir(parents=True, exist_ok=True)
                analysis_ctx.extra["wind_monitor_state"] = {{
                    "mission_completed_full": True,
                    "square_completed": True,
                    "loiter_completed": True,
                }}
                bin_path = root / "source.BIN"
                bin_path.write_bytes(b"bin")
                analyzer = WindMatrixAnalyzer(cfg)

                with (
                    mock.patch.object(
                        wind_analyzers,
                        "cleanup_stack_for_analysis",
                        return_value=None,
                    ),
                    mock.patch.object(
                        wind_analyzers,
                        "clamp_timeout_to_slot",
                        return_value=0.0,
                    ),
                    mock.patch.object(
                        wind_analyzers,
                        "collect_bin_log",
                        return_value=bin_path,
                    ),
                    mock.patch.object(
                        wind_analyzers,
                        "ensure_run_alias_link",
                        return_value=None,
                    ),
                    mock.patch.object(
                        wind_analyzers,
                        "run_analysis",
                        return_value=None,
                    ),
                    mock.patch.object(
                        wind_analyzers,
                        "build_run_summary",
                        return_value={{}},
                    ),
                    mock.patch.object(
                        wind_analyzers.time,
                        "sleep",
                        return_value=None,
                    ),
                ):
                    result = analyzer.analyze(cases[0], analysis_ctx)
                    assert result.ok is True

                manifest = WindMatrixManifest(root)
                record = AttemptRecord(
                    attempt_id="wind_x_00_y_04__rep_01__attempt_001",
                    suite_name="wind_matrix",
                    case_id="wind_x_00_y_04",
                    target_run_index=1,
                    attempt_index=1,
                    status=AttemptStatus.SUCCESS,
                    verdict=Verdict(VerdictClass.SUCCESS, "success_full", False),
                    parameters={{"wind_x_mps": 0, "wind_y_mps": 4}},
                    stimulus_result={{"kind": "wind_matrix"}},
                    plugin_manifest_fields={{
                        "attempt_id": "wind_x_00_y_04__rep_01__attempt_001",
                        "combo_key": "wind_x_00_y_04",
                        "x_wind_mps": 0,
                        "y_wind_mps": 4,
                        "target_run_index": 1,
                        "attempt_index": 1,
                        "status": "success_full",
                        "analysis_status": "done",
                    }},
                )
                manifest.append_attempt(record)
                saved = manifest.load()["attempts"][0]
                assert saved["combo_key"] == "wind_x_00_y_04"
                assert saved["schema_version"] == "test_suite.generic_manifest.v1"
                assert manifest.generic_view()["attempts"][0]["case_id"] == "wind_x_00_y_04"

                plugin = build_plugin(cfg)
                runner = plugin.attempt_runner()
                assert isinstance(runner._strategy, StagedStrategy)
                assert not isinstance(runner._strategy, LegacyDelegateStrategy)
                assert str(
                    plugin.attempt_dir_factory()(plugin.manifest, cases[0], 1)
                ).endswith(
                    "wind_x_00_y_04/runs/attempt_001"
                )

                with mock.patch.object(sys, "argv", ["run_case", "--x", "0", "--y", "4", "--rep", "1"]):
                    assert run_case._parse_args().attempt_strategy == "legacy"
                with mock.patch.object(sys, "argv", ["run_suite", "--attempt-strategy", "staged"]):
                    suite_args = run_suite._parse_args()
                    assert suite_args.attempt_strategy == "staged"
                    assert suite_args.auto_wind_phase == DEFAULT_STAGED_AUTO_WIND_PHASE
                with mock.patch.object(sys, "argv", ["run_round_robin", "--attempt-strategy", "staged"]):
                    rr_args = run_round_robin._parse_args()
                    assert rr_args.attempt_strategy == "staged"
                    assert rr_args.auto_wind_phase == DEFAULT_STAGED_AUTO_WIND_PHASE

                def noop_run(self):
                    return []

                with (
                    mock.patch.object(SuiteRunner, "run", noop_run),
                    mock.patch.object(sys, "argv", [
                        "run_suite",
                        "--attempt-strategy", "staged",
                        "--auto-wind-phase", "before-arm",
                        "--campaign-root", str(root / "suite_cli"),
                        "--x-values", "0",
                        "--y-values", "4",
                        "--runs-per-combo", "1",
                    ]),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    run_suite.main()

                with (
                    mock.patch.object(SuiteRunner, "run", noop_run),
                    mock.patch.object(sys, "argv", [
                        "run_round_robin",
                        "--attempt-strategy", "staged",
                        "--auto-wind-phase", "before-arm",
                        "--campaign-root", str(root / "rr_cli"),
                        "--x-values", "0",
                        "--y-values", "4",
                        "--runs-per-combo", "1",
                        "--slot-minutes", "1",
                    ]),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    run_round_robin.main()

                # Phase 3D: prove env.launch()+cleanup() run with legacy runner
                # imports blocked and no real processes spawn.
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import runtime as wm_runtime
                from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.environment import WindMatrixEnvironment

                class _FakePopen3D:
                    def poll(self):
                        return None

                class _FakeHandle3D:
                    def close(self):
                        pass

                launch_cfg = WindMatrixConfig(
                    campaign_root=root,
                    x_values=(0,),
                    y_values=(4,),
                    launch_stack=True,
                    auto_control=False,
                    attempt_strategy="staged",
                )
                env3d = WindMatrixEnvironment(launch_cfg)
                launch_case = cases[0]
                launch_ctx = AttemptContext(
                    case=launch_case,
                    campaign_root=root,
                    attempt_dir=defaults.attempt_dir(root, launch_case.case_id, 2),
                    attempt_index=2,
                    target_run_index=1,
                    start_wall_s=0.0,
                    start_monotonic_s=0.0,
                )
                _fake_sitl = (_FakePopen3D(), _FakeHandle3D())
                _fake_gazebo = (_FakePopen3D(), _FakeHandle3D())
                with (
                    mock.patch.object(wm_runtime, "cleanup_stack", return_value=None),
                    mock.patch.object(wm_runtime, "launch_sitl", return_value=_fake_sitl),
                    mock.patch.object(wm_runtime, "launch_gazebo", return_value=_fake_gazebo),
                    mock.patch.object(wm_runtime, "ensure_process_alive", return_value=None),
                    mock.patch.object(wm_runtime, "write_static_wind_world", return_value=root / "world.sdf"),
                    mock.patch("sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.environment.time.sleep", return_value=None),
                ):
                    env3d.launch(launch_case, launch_ctx)
                    env3d.cleanup(launch_case, launch_ctx)
                assert "sitl" in launch_ctx.process_handles, "sitl proc handle missing after launch"
                assert "gazebo" in launch_ctx.process_handles, "gazebo proc handle missing after launch"

                imported = sorted(name for name in blocked if name in sys.modules)
                assert imported == [], imported
                print(json.dumps({{"case_ids": [case.case_id for case in cases]}}))
                """
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [str(ROOT / "env" / "bin" / "python3"), "-c", code],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual("", result.stderr)
        self.assertEqual(0, result.returncode)
        self.assertEqual(
            {"case_ids": ["wind_x_00_y_04"]},
            json.loads(result.stdout),
        )


class Phase3DEnvironmentOwnershipTests(unittest.TestCase):
    """Phase 3D: WindMatrixEnvironment.launch/cleanup use owned runtime, not legacy."""

    def test_phase3d_environment_launch_uses_owned_runtime_not_legacy(self) -> None:
        from unittest.mock import MagicMock, patch

        from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import defaults as wm_defaults
        from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import runtime as wm_runtime
        from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.config import WindMatrixConfig
        from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.environment import WindMatrixEnvironment
        from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.plugin import build_plugin
        from sim_ard_gaw.campaigns.test_suite.core.models import AttemptContext, TestCase

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            cfg = WindMatrixConfig(
                campaign_root=root,
                x_values=(0,),
                y_values=(4,),
                launch_stack=True,
                auto_control=False,
                attempt_strategy="staged",
            )
            plugin = build_plugin(cfg)
            env = plugin.environment

            case = TestCase(
                suite_name="wind_matrix",
                case_id="wind_x_00_y_04",
                parameters={"wind_x_mps": 0, "wind_y_mps": 4},
            )
            ctx = AttemptContext(
                case=case,
                campaign_root=root,
                attempt_dir=wm_defaults.attempt_dir(root, case.case_id, 1),
                attempt_index=1,
                target_run_index=1,
                start_wall_s=0.0,
                start_monotonic_s=0.0,
            )

            class _FakePopen:
                def poll(self) -> None:
                    return None

            class _FakeHandle:
                def close(self) -> None:
                    pass

            _fake_sitl = (_FakePopen(), _FakeHandle())
            _fake_gazebo = (_FakePopen(), _FakeHandle())

            legacy_blocker = MagicMock(side_effect=AssertionError("legacy used in launch/cleanup"))

            with (
                patch(
                    "sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.legacy.run_matrix_module",
                    legacy_blocker,
                ),
                patch(
                    "sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.legacy.run_one_module",
                    legacy_blocker,
                ),
                patch.object(wm_runtime, "cleanup_stack", return_value=None),
                patch.object(wm_runtime, "launch_sitl", return_value=_fake_sitl),
                patch.object(wm_runtime, "launch_gazebo", return_value=_fake_gazebo),
                patch.object(wm_runtime, "ensure_process_alive", return_value=None),
                patch.object(
                    wm_runtime,
                    "write_static_wind_world",
                    return_value=root / "world.sdf",
                ),
                patch(
                    "sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.environment.time.sleep",
                    return_value=None,
                ),
            ):
                env.launch(case, ctx)
                env.cleanup(case, ctx)

            self.assertIn("sitl", ctx.process_handles)
            self.assertIn("gazebo", ctx.process_handles)
            legacy_blocker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
