from __future__ import annotations

# pyright: reportMissingImports=false

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "src" / "sim_ard_gaw" / "compat_scripts"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(SCRIPTS))

import run_one  # noqa: E402
from test_suite.core import _legacy  # noqa: E402
from test_suite.core.analysis import Analyzer, AnalyzerChain  # noqa: E402
from test_suite.core.attempt_runner import (  # noqa: E402
    AttemptRunner,
    LegacyDelegateStrategy,
    StagedStrategy,
)
from test_suite.core.control import ControlStrategy  # noqa: E402
from test_suite.core.environment import EnvironmentAdapter  # noqa: E402
from test_suite.core.manifest import LegacyManifest  # noqa: E402
from test_suite.core.models import (  # noqa: E402
    AnalysisResult,
    AttemptContext,
    AttemptRecord,
    AttemptStatus,
    MonitorResult,
    TestCase,
    Verdict,
    VerdictClass,
)
from test_suite.core.monitor import CompletionMonitor  # noqa: E402
from test_suite.core.stimulus import StimulusAdapter  # noqa: E402
from test_suite.plugins.wind_matrix.config import WindMatrixConfig  # noqa: E402
from test_suite.plugins.wind_matrix.analyzers import WindMatrixAnalyzer  # noqa: E402
from test_suite.plugins.wind_matrix.plugin import build_plugin  # noqa: E402
from test_suite.plugins.wind_matrix.analyzers import WindMatrixVerdictPolicy  # noqa: E402


class _FakeManifest:
    def __init__(self) -> None:
        self.records: list[AttemptRecord] = []

    def load(self) -> dict[str, Any]:
        return {"attempts": []}

    def save(self, manifest: dict[str, Any]) -> None:
        return None

    def accepted_count(self, case: TestCase) -> int:
        return 0

    def next_attempt_index(self, case: TestCase) -> int:
        return 1

    def append_attempt(self, record: AttemptRecord) -> None:
        self.records.append(record)


class _RecordingEnvironment(EnvironmentAdapter):
    def __init__(self, events: list[str], cleanup_raises: bool = False) -> None:
        self.events = events
        self.cleanup_raises = cleanup_raises

    def prepare_case(self, case: TestCase) -> None:
        self.events.append("prepare")

    def launch(self, case: TestCase, ctx: AttemptContext) -> None:
        self.events.append("launch")

    def assert_ready(self, case: TestCase, ctx: AttemptContext) -> None:
        self.events.append("ready")

    def cleanup(self, case: TestCase, ctx: AttemptContext) -> None:
        self.events.append("cleanup")
        if self.cleanup_raises:
            raise RuntimeError("cleanup failed")


class _RecordingStimulus(StimulusAdapter):
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def apply(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
        self.events.append("stimulus.apply")
        return {"kind": "fake"}

    def verify(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
        self.events.append("stimulus.verify")
        return {"ok": True}


class _FailingStimulus(StimulusAdapter):
    def apply(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
        raise RuntimeError("stimulus boom")


class _RecordingControl(ControlStrategy):
    def __init__(self, events: list[str], error: BaseException | None = None) -> None:
        self.events = events
        self.error = error

    def execute(self, case: TestCase, ctx: AttemptContext) -> None:
        self.events.append("control")
        if self.error is not None:
            raise self.error


class _RecordingMonitor(CompletionMonitor):
    def __init__(self, events: list[str], completed: bool = True) -> None:
        self.events = events
        self.completed = completed

    def run(self, case: TestCase, ctx: AttemptContext) -> MonitorResult:
        self.events.append("monitor")
        return MonitorResult(
            completed=self.completed,
            reason="done" if self.completed else "partial",
            duration_s=1.0,
        )


class _FailingMonitor(CompletionMonitor):
    def run(self, case: TestCase, ctx: AttemptContext) -> MonitorResult:
        raise RuntimeError("monitor boom")


class _RecordingAnalyzer(Analyzer):
    name = "recording"

    def __init__(self, events: list[str], ok: bool = True) -> None:
        self.events = events
        self.ok = ok

    def analyze(self, case: TestCase, ctx: AttemptContext) -> AnalysisResult:
        self.events.append("analyze")
        return AnalysisResult("recording", self.ok, {"ok": self.ok})


class _StaticVerdict:
    def __init__(self, events: list[str], klass: VerdictClass) -> None:
        self.events = events
        self.klass = klass

    def classify(self, case, monitor_result, analysis_results) -> Verdict:
        self.events.append("verdict")
        return Verdict(
            klass=self.klass,
            reason=self.klass.value,
            retryable=self.klass == VerdictClass.FAILED_RETRYABLE,
        )


def _case() -> TestCase:
    return TestCase(
        suite_name="wind_matrix",
        case_id="wind_x_00_y_04",
        parameters={"wind_x_mps": 0, "wind_y_mps": 4},
    )


def _runner(
    events: list[str],
    *,
    control_error: BaseException | None = None,
    verdict_class: VerdictClass = VerdictClass.SUCCESS,
) -> tuple[AttemptRunner, _FakeManifest]:
    manifest = _FakeManifest()
    strategy = StagedStrategy(
        stimulus=_RecordingStimulus(events),
        control=_RecordingControl(events, control_error),
        monitor=_RecordingMonitor(events),
        analyzers=AnalyzerChain([_RecordingAnalyzer(events)]),
        verdict_policy=_StaticVerdict(events, verdict_class),  # type: ignore[arg-type]
    )
    return (
        AttemptRunner(
            environment=_RecordingEnvironment(events),
            strategy=strategy,
            manifest=manifest,  # type: ignore[arg-type]
            artifact_root=Path("/tmp/campaign"),
            log=lambda _msg: None,
        ),
        manifest,
    )


class Phase3StagedAttemptTests(unittest.TestCase):
    def test_staged_strategy_calls_stages_in_expected_order(self) -> None:
        events: list[str] = []
        runner, manifest = _runner(events)

        runner.run(_case(), 1, 1, Path("/tmp/attempt"))

        self.assertEqual(
            [
                "prepare",
                "launch",
                "ready",
                "stimulus.apply",
                "stimulus.verify",
                "control",
                "monitor",
                "analyze",
                "verdict",
                "cleanup",
            ],
            events,
        )
        self.assertEqual(AttemptStatus.SUCCESS, manifest.records[0].status)

    def test_cleanup_runs_on_success(self) -> None:
        events: list[str] = []
        runner, _manifest = _runner(events)

        runner.run(_case(), 1, 1, Path("/tmp/attempt"))

        self.assertIn("cleanup", events)

    def test_cleanup_runs_on_failure(self) -> None:
        events: list[str] = []
        runner, _manifest = _runner(
            events, control_error=RuntimeError("control failed")
        )

        with self.assertRaises(RuntimeError):
            runner.run(_case(), 1, 1, Path("/tmp/attempt"))

        self.assertIn("cleanup", events)

    def test_cleanup_runs_on_interrupt_like_error(self) -> None:
        events: list[str] = []
        runner, _manifest = _runner(events, control_error=KeyboardInterrupt())

        with self.assertRaises(KeyboardInterrupt):
            runner.run(_case(), 1, 1, Path("/tmp/attempt"))

        self.assertIn("cleanup", events)

    def test_partial_verdict_stays_partial(self) -> None:
        events: list[str] = []
        runner, manifest = _runner(events, verdict_class=VerdictClass.PARTIAL)

        record = runner.run(_case(), 1, 1, Path("/tmp/attempt"))

        self.assertEqual(AttemptStatus.PARTIAL, record.status)
        self.assertEqual(AttemptStatus.PARTIAL, manifest.records[0].status)

    def test_failed_error_interrupted_do_not_count_as_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_one.save_manifest(root, {
                "campaign_root": str(root),
                "attempts": [
                    {
                        "attempt_id": f"wind_x_00_y_04__rep_01__attempt_{idx:03d}",
                        "combo_key": "wind_x_00_y_04",
                        "status": status,
                        "analysis_status": "not_run",
                    }
                    for idx, status in enumerate(
                        ("failed", "error", "interrupted"), start=1
                    )
                ],
            })

            self.assertEqual(0, LegacyManifest(root).accepted_count(_case()))

    def test_plugin_manifest_fields_are_additive_for_new_staged_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_one.save_manifest(root, {"campaign_root": str(root), "attempts": []})
            record = AttemptRecord(
                attempt_id="wind_x_00_y_04__rep_01__attempt_001",
                suite_name="wind_matrix",
                case_id="wind_x_00_y_04",
                target_run_index=1,
                attempt_index=1,
                status=AttemptStatus.SUCCESS,
                verdict=Verdict(VerdictClass.SUCCESS, "success_full", False),
                start_time_utc="2026-05-25T00:00:00Z",
                end_time_utc="2026-05-25T00:10:00Z",
                parameters={"wind_x_mps": 0, "wind_y_mps": 4},
                stimulus_result={"kind": "wind_matrix"},
                plugin_manifest_fields={
                    "attempt_id": "wind_x_00_y_04__rep_01__attempt_001",
                    "combo_key": "wind_x_00_y_04",
                    "x_wind_mps": 0,
                    "y_wind_mps": 4,
                    "status": "success_full",
                    "analysis_status": "done",
                    "start_time_utc": "2026-05-25T00:00:00Z",
                    "end_time_utc": "2026-05-25T00:10:00Z",
                },
            )

            LegacyManifest(root).append_attempt(record)
            saved = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            attempt = saved["attempts"][0]

            self.assertEqual("wind_x_00_y_04", attempt["combo_key"])
            self.assertEqual("success_full", attempt["status"])
            self.assertEqual("done", attempt["analysis_status"])
            self.assertEqual("test_suite.generic_manifest.v1", attempt["schema_version"])
            self.assertEqual("wind_matrix", attempt["suite_name"])
            self.assertEqual({"wind_x_mps": 0, "wind_y_mps": 4}, attempt["parameters"])

    def test_legacy_manifest_fields_round_trip_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy_row = {
                "attempt_id": "wind_x_00_y_04__rep_01__attempt_001",
                "combo_key": "wind_x_00_y_04",
                "x_wind_mps": 0,
                "y_wind_mps": 4,
                "status": "success_full",
                "analysis_status": "done",
                "start_time_utc": "2026-05-25T00:00:00Z",
                "end_time_utc": "2026-05-25T00:10:00Z",
            }
            run_one.save_manifest(root, {
                "campaign_root": str(root),
                "attempts": [dict(legacy_row)],
            })
            LegacyManifest(root).append_attempt(
                AttemptRecord(
                    attempt_id=legacy_row["attempt_id"],
                    suite_name="wind_matrix",
                    case_id="wind_x_00_y_04",
                    target_run_index=1,
                    attempt_index=1,
                    status=AttemptStatus.SUCCESS,
                    verdict=Verdict(VerdictClass.SUCCESS, "success_full", False),
                    start_time_utc=legacy_row["start_time_utc"],
                    end_time_utc=legacy_row["end_time_utc"],
                    parameters={"wind_x_mps": 0, "wind_y_mps": 4},
                    stimulus_result={"kind": "wind_matrix"},
                )
            )
            saved = LegacyManifest(root).load()["attempts"][0]

            for key, value in legacy_row.items():
                self.assertEqual(value, saved[key])

    def test_wind_plugin_can_build_staged_strategy_without_compat_wrappers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = build_plugin(
                WindMatrixConfig(
                    campaign_root=Path(temp_dir),
                    launch_stack=False,
                    auto_control=False,
                    attempt_strategy="staged",
                )
            )

            strategy = plugin.attempt_runner()._strategy  # noqa: SLF001
            self.assertIsInstance(strategy, StagedStrategy)
            self.assertNotIsInstance(strategy, LegacyDelegateStrategy)
            self.assertIn(
                "test_suite.plugins.wind_matrix",
                type(strategy.stimulus).__module__,
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            code = (
                "from pathlib import Path\n"
                "from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix import build_plugin\n"
                "from sim_ard_gaw.campaigns.test_suite.plugins.wind_matrix.config import WindMatrixConfig\n"
                f"plugin = build_plugin(WindMatrixConfig(campaign_root=Path({temp_dir!r}), "
                "launch_stack=False, auto_control=False, attempt_strategy='staged'))\n"
                "print(type(plugin.attempt_runner()._strategy).__name__)\n"
            )
            result = subprocess.run(
                [str(ROOT / "env" / "bin" / "python3"), "-c", code],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.stderr, "")
            self.assertEqual(0, result.returncode)
            self.assertEqual("StagedStrategy", result.stdout.strip())

    def test_legacy_delegate_path_remains_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = build_plugin(
                WindMatrixConfig(
                    campaign_root=Path(temp_dir),
                    launch_stack=False,
                    attempt_strategy="legacy",
                )
            )

            self.assertIsInstance(
                plugin.attempt_runner()._strategy,  # noqa: SLF001
                LegacyDelegateStrategy,
            )
            self.assertTrue(callable(plugin.legacy_body))

    def test_square_loiter_early_cleanup_and_flush_happen_before_bin_collection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            attempt_dir = root / "wind_x_00_y_04" / "runs" / "attempt_001"
            attempt_dir.mkdir(parents=True)
            source_bin = root / "source.BIN"
            source_bin.write_bytes(b"bin")
            events: list[str] = []
            case = _case()
            ctx = AttemptContext(
                case=case,
                campaign_root=root,
                attempt_dir=attempt_dir,
                attempt_index=1,
                target_run_index=1,
                start_wall_s=0.0,
                start_monotonic_s=0.0,
            )
            ctx.extra["wind_monitor_state"] = {
                "completed_square_loiter_early": True,
                "mission_completed_full": False,
                "square_completed": True,
                "loiter_completed": True,
            }
            owned_run_one = _legacy.run_one_module()
            analyzer = WindMatrixAnalyzer(
                WindMatrixConfig(
                    campaign_root=root,
                    accept_square_only=True,
                    require_analysis=False,
                )
            )

            with (
                patch.object(owned_run_one, "cleanup_stack_for_analysis", side_effect=lambda: events.append("cleanup")),
                patch.object(owned_run_one, "clamp_timeout_to_slot", side_effect=lambda *args, **kwargs: events.append("clamp") or 0.0),
                patch("test_suite.plugins.wind_matrix.analyzers.time.sleep", side_effect=lambda _s: events.append("sleep")),
                patch.object(owned_run_one, "collect_bin_log", side_effect=lambda *args, **kwargs: events.append("collect") or source_bin),
                patch.object(owned_run_one, "run_analysis", side_effect=lambda *args, **kwargs: events.append("analysis")),
                patch.object(owned_run_one, "build_run_summary", return_value={}),
                patch.object(owned_run_one, "ensure_run_alias_link", side_effect=lambda *args, **kwargs: events.append("alias")),
            ):
                result = analyzer.analyze(case, ctx)

            self.assertEqual("success_square_only", result.summary["legacy_status"])
            self.assertEqual(["cleanup", "clamp", "sleep", "collect", "alias", "analysis"], events)
            self.assertEqual(
                "success_square_only",
                ctx.extra["plugin_manifest_fields"]["status"],
            )

    def test_collect_bin_failure_persists_legacy_compatible_error_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_one.save_manifest(root, {"campaign_root": str(root), "attempts": []})
            case = _case()

            class _NoopStimulus(StimulusAdapter):
                def apply(self, case: TestCase, ctx: AttemptContext) -> dict[str, Any]:
                    return {"kind": "none"}

            class _NoopControl(ControlStrategy):
                def execute(self, case: TestCase, ctx: AttemptContext) -> None:
                    return None

            class _CompletedMonitor(CompletionMonitor):
                def run(self, case: TestCase, ctx: AttemptContext) -> MonitorResult:
                    ctx.extra["wind_monitor_state"] = {
                        "mission_completed_full": True,
                        "square_completed": True,
                        "loiter_completed": True,
                    }
                    return MonitorResult(True, "completed", 1.0)

            strategy = StagedStrategy(
                stimulus=_NoopStimulus(),
                control=_NoopControl(),
                monitor=_CompletedMonitor(),
                analyzers=AnalyzerChain([
                    WindMatrixAnalyzer(WindMatrixConfig(campaign_root=root))
                ]),
                verdict_policy=WindMatrixVerdictPolicy(),
            )
            runner = AttemptRunner(
                environment=_RecordingEnvironment([]),
                strategy=strategy,
                manifest=LegacyManifest(root),
                artifact_root=root,
                log=lambda _msg: None,
            )
            owned_run_one = _legacy.run_one_module()
            with (
                patch.object(owned_run_one, "clamp_timeout_to_slot", return_value=0.0),
                patch("test_suite.plugins.wind_matrix.analyzers.time.sleep", return_value=None),
                patch.object(owned_run_one, "collect_bin_log", return_value=None),
            ):
                record = runner.run(
                    case=case,
                    target_run_index=1,
                    attempt_index=1,
                    attempt_dir=root / "wind_x_00_y_04" / "runs" / "attempt_001",
                )

            saved = LegacyManifest(root).load()["attempts"][0]
            self.assertEqual(AttemptStatus.ERROR, record.status)
            self.assertEqual("wind_x_00_y_04__rep_01__attempt_001", saved["attempt_id"])
            self.assertEqual("wind_x_00_y_04", saved["combo_key"])
            self.assertEqual(0, saved["x_wind_mps"])
            self.assertEqual(4, saved["y_wind_mps"])
            self.assertEqual("error", saved["status"])
            self.assertEqual("not_run", saved["analysis_status"])
            self.assertEqual(
                str(root / "wind_x_00_y_04" / "runs" / "attempt_001"),
                saved["attempt_dir"],
            )
            self.assertEqual("test_suite.generic_manifest.v1", saved["schema_version"])
            self.assertEqual("wind_x_00_y_04", saved["case_id"])

    def test_staged_after_takeoff_rejected_before_environment_launch(self) -> None:
        events: list[str] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "after-takeoff"):
                build_plugin(
                    WindMatrixConfig(
                        campaign_root=Path(temp_dir),
                        launch_stack=True,
                        auto_control=True,
                        auto_wind_phase="after-takeoff",
                        attempt_strategy="staged",
                    )
                )
        self.assertEqual([], events)

    def test_staged_stimulus_failure_persists_legacy_error_row_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin = build_plugin(
                WindMatrixConfig(
                    campaign_root=root,
                    launch_stack=False,
                    auto_control=False,
                    attempt_strategy="staged",
                )
            )
            assert isinstance(plugin.staged_strategy, StagedStrategy)
            plugin.staged_strategy.stimulus = _FailingStimulus()
            events: list[str] = []
            runner = AttemptRunner(
                environment=_RecordingEnvironment(events),
                strategy=plugin.staged_strategy,
                manifest=plugin.manifest,
                artifact_root=root,
                log=lambda _msg: None,
            )

            record = runner.run(
                case=_case(),
                target_run_index=1,
                attempt_index=1,
                attempt_dir=root / "wind_x_00_y_04" / "runs",
            )

            self.assertIn("cleanup", events)
            self.assertEqual(AttemptStatus.ERROR, record.status)
            self._assert_legacy_compatible_error_row(root)
            self.assertEqual(0, LegacyManifest(root).accepted_count(_case()))

    def test_staged_control_and_monitor_failures_persist_legacy_error_rows(self) -> None:
        for failing_stage in ("control", "monitor"):
            with self.subTest(failing_stage=failing_stage):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    plugin = build_plugin(
                        WindMatrixConfig(
                            campaign_root=root,
                            launch_stack=False,
                            auto_control=False,
                            attempt_strategy="staged",
                        )
                    )
                    assert isinstance(plugin.staged_strategy, StagedStrategy)
                    plugin.staged_strategy.stimulus = _RecordingStimulus([])
                    if failing_stage == "control":
                        plugin.staged_strategy.control = _RecordingControl(
                            [], RuntimeError("control boom"),
                        )
                    else:
                        plugin.staged_strategy.control = _RecordingControl([])
                        plugin.staged_strategy.monitor = _FailingMonitor()
                    events: list[str] = []
                    runner = AttemptRunner(
                        environment=_RecordingEnvironment(events),
                        strategy=plugin.staged_strategy,
                        manifest=plugin.manifest,
                        artifact_root=root,
                        log=lambda _msg: None,
                    )

                    record = runner.run(
                        case=_case(),
                        target_run_index=1,
                        attempt_index=1,
                        attempt_dir=root / "wind_x_00_y_04" / "runs",
                    )

                    self.assertIn("cleanup", events)
                    self.assertEqual(AttemptStatus.ERROR, record.status)
                    self._assert_legacy_compatible_error_row(root)
                    self.assertEqual(0, LegacyManifest(root).accepted_count(_case()))

    def _assert_legacy_compatible_error_row(self, root: Path) -> None:
        saved = LegacyManifest(root).load()["attempts"][0]
        self.assertEqual("wind_x_00_y_04__rep_01__attempt_001", saved["attempt_id"])
        self.assertEqual("wind_x_00_y_04", saved["combo_key"])
        self.assertEqual(0, saved["x_wind_mps"])
        self.assertEqual(4, saved["y_wind_mps"])
        self.assertEqual("error", saved["status"])
        self.assertEqual("not_run", saved["analysis_status"])
        self.assertEqual(
            str(root / "wind_x_00_y_04" / "runs" / "attempt_001"),
            saved["attempt_dir"],
        )
        self.assertIsNone(saved["raw_log_path"])
        self.assertEqual("test_suite.generic_manifest.v1", saved["schema_version"])
        self.assertEqual("wind_x_00_y_04", saved["case_id"])
        self.assertEqual({"wind_x_mps": 0, "wind_y_mps": 4}, saved["parameters"])


if __name__ == "__main__":
    os.environ.setdefault(
        "PYTHONPATH", os.pathsep.join([str(ROOT / "src"), str(SCRIPTS)])
    )
    unittest.main()
