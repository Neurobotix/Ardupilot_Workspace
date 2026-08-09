"""Round-robin parity contract across campaign lanes.

`RoundRobinScheduler` is a core, sensor-agnostic capability. These tests pin
the two properties that let every lane reach it through one path without
changing how any lane already schedules:

1. Progress is a lane property (`Manifest.progress_count`), defaulting to
   `accepted_count` so lanes that never override it are unaffected.
2. The slot budget is optional, so a lane whose attempt length is governed by
   its own mission timeout publishes no deadline and has no phase timeout
   clamped.

The GPS ordering cases below replay the hand-rolled campaign loop that
`run_live_round_robin_campaign` used before it moved onto `SuiteRunner`, and
assert the scheduler reproduces its schedule exactly.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sim_ard_gaw.campaigns.test_suite.core.models import TestCase
from sim_ard_gaw.campaigns.test_suite.core.scheduler import (
    RoundRobinScheduler,
    SequentialScheduler,
)


class _ScriptedManifest:
    """Manifest stub driven by a scripted list of attempt outcomes.

    Each outcome is `(case_id, workflow_complete, accepted)`. `progress_key`
    selects which counter the scheduler sees, mirroring a lane that overrides
    `progress_count` versus one that does not.
    """

    def __init__(self, outcomes, progress_key="accepted"):
        self._outcomes = list(outcomes)
        self._done: list[tuple[str, bool, bool]] = []
        self._progress_key = progress_key

    def record(self, case_id):
        outcome = self._outcomes.pop(0)
        assert outcome[0] == case_id, f"script expected {outcome[0]}, got {case_id}"
        self._done.append(outcome)
        return outcome

    def accepted_count(self, case):
        return sum(1 for c, _w, a in self._done if c == case.case_id and a)

    def workflow_complete_count(self, case):
        return sum(1 for c, w, _a in self._done if c == case.case_id and w)

    def progress_count(self, case):
        if self._progress_key == "workflow":
            return self.workflow_complete_count(case)
        return self.accepted_count(case)

    def next_attempt_index(self, case):
        return sum(1 for c, _w, _a in self._done if c == case.case_id) + 1


def _cases(case_ids, target_runs, suite="gps_failure"):
    return [
        TestCase(
            case_id=case_id,
            suite_name=suite,
            mission_file=Path("mission.txt"),
            parameters={},
            acceptance_target_runs=target_runs,
        )
        for case_id in case_ids
    ]


def _legacy_gps_schedule(case_ids, runs_per_case, outcomes):
    """The pre-parity hand-rolled GPS campaign loop, preserved as the oracle."""
    manifest = _ScriptedManifest(outcomes, progress_key="workflow")
    cases = _cases(case_ids, runs_per_case)
    schedule = []
    round_index = 0
    while True:
        active = [
            case
            for case in cases
            if manifest.workflow_complete_count(case) < runs_per_case
        ]
        if not active:
            return schedule
        round_index += 1
        for case in active:
            target_run_index = manifest.workflow_complete_count(case) + 1
            schedule.append((case.case_id, target_run_index, round_index))
            workflow_complete = manifest.record(case.case_id)[1]
            if not workflow_complete:
                return schedule  # campaign stop rule: workflow failure is fatal


def _scheduler_gps_schedule(case_ids, runs_per_case, outcomes):
    """The same campaign driven by the core round-robin scheduler."""
    manifest = _ScriptedManifest(outcomes, progress_key="workflow")
    cases = _cases(case_ids, runs_per_case)
    scheduler = RoundRobinScheduler(
        per_attempt_budget_s=None,
        max_passes=runs_per_case,
    )
    pending = scheduler.initial_pending(cases, manifest)
    schedule = []
    while True:
        decision = scheduler.next_case(pending, manifest)
        if decision.case is None:
            return schedule
        assert decision.slot_deadline_monotonic_s is None
        target_run_index = manifest.progress_count(decision.case) + 1
        schedule.append(
            (decision.case.case_id, target_run_index, decision.metadata["pass_index"])
        )
        workflow_complete = manifest.record(decision.case.case_id)[1]
        if not workflow_complete:
            return schedule


class ProgressCountDefaultTests(unittest.TestCase):
    def test_default_progress_count_is_accepted_count(self):
        """A lane that does not override progress_count schedules as before."""
        manifest = _ScriptedManifest([], progress_key="accepted")
        case = _cases(["c1"], 2)[0]
        manifest._done = [("c1", True, False), ("c1", True, True)]
        # accepted=1 even though two runs were workflow-complete.
        self.assertEqual(1, manifest.progress_count(case))

    def test_gps_manifest_overrides_progress_to_workflow_complete(self):
        from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.manifest import (
            GpsFailureManifest,
        )

        self.assertIsNot(
            GpsFailureManifest.progress_count,
            GpsFailureManifest.accepted_count,
        )


class SlotBudgetTests(unittest.TestCase):
    def test_budget_none_publishes_no_deadline(self):
        """No budget means no deadline, so no phase timeout gets clamped."""
        manifest = _ScriptedManifest([], progress_key="accepted")
        cases = _cases(["c1"], 1)
        scheduler = RoundRobinScheduler(per_attempt_budget_s=None)
        decision = scheduler.next_case(cases, manifest)

        self.assertIsNone(decision.slot_deadline_monotonic_s)
        self.assertNotIn("slot_budget_s", decision.metadata)
        self.assertEqual(1, decision.metadata["pass_index"])

    def test_budget_set_still_publishes_deadline_and_budget(self):
        """wind_matrix keeps its bounded slot behavior unchanged."""
        manifest = _ScriptedManifest([], progress_key="accepted")
        cases = _cases(["c1"], 1, suite="wind_matrix")
        scheduler = RoundRobinScheduler(per_attempt_budget_s=600.0)
        decision = scheduler.next_case(cases, manifest)

        self.assertIsNotNone(decision.slot_deadline_monotonic_s)
        self.assertEqual(600.0, decision.metadata["slot_budget_s"])

    def test_zero_or_negative_budget_still_rejected(self):
        for bad in (0, -1.0):
            with self.assertRaises(ValueError):
                RoundRobinScheduler(per_attempt_budget_s=bad)


class GpsSchedulingEquivalenceTests(unittest.TestCase):
    """The scheduler must reproduce the legacy GPS loop's exact schedule."""

    def _assert_equivalent(self, case_ids, runs, outcomes):
        self.assertEqual(
            _legacy_gps_schedule(case_ids, runs, outcomes),
            _scheduler_gps_schedule(case_ids, runs, outcomes),
        )

    def test_all_runs_accepted(self):
        ids = ["nominal", "slow_drift_0p5_mps", "hard_denial_15s"]
        self._assert_equivalent(
            ids, 2, [(c, True, True) for _ in range(2) for c in ids]
        )

    def test_workflow_complete_but_unaccepted_still_counts_as_progress(self):
        """The divergence that makes accepted_count wrong for this lane.

        These runs flew and injected cleanly but their behavior was not
        accepted. They are spent physical repetitions, so the campaign must
        not re-fly them.
        """
        ids = ["nominal", "slow_drift_0p5_mps"]
        self._assert_equivalent(
            ids, 2, [(c, True, False) for _ in range(2) for c in ids]
        )

    def test_mixed_acceptance(self):
        self._assert_equivalent(
            ["nominal", "slow_drift_0p5_mps"],
            2,
            [
                ("nominal", True, True),
                ("slow_drift_0p5_mps", True, False),
                ("nominal", True, False),
                ("slow_drift_0p5_mps", True, True),
            ],
        )

    def test_fatal_workflow_failure_stops_campaign(self):
        self._assert_equivalent(
            ["nominal", "slow_drift_0p5_mps", "hard_denial_15s"],
            2,
            [("nominal", True, True), ("slow_drift_0p5_mps", False, False)],
        )

    def test_single_case_single_run_validation_rerun_shape(self):
        self._assert_equivalent(["nominal"], 1, [("nominal", True, True)])

    def test_max_passes_bounds_the_campaign(self):
        ids = ["nominal", "slow_drift_0p5_mps"]
        schedule = _scheduler_gps_schedule(
            ids, 1, [(c, True, True) for c in ids]
        )
        self.assertEqual(
            [("nominal", 1, 1), ("slow_drift_0p5_mps", 1, 1)], schedule
        )


class SequentialUnaffectedTests(unittest.TestCase):
    def test_sequential_drains_each_case_before_moving_on(self):
        manifest = _ScriptedManifest([], progress_key="accepted")
        cases = _cases(["c1", "c2"], 2, suite="airspeed_failure")
        scheduler = SequentialScheduler()

        decision = scheduler.next_case(cases, manifest)
        self.assertEqual("c1", decision.case.case_id)
        self.assertIsNone(decision.slot_deadline_monotonic_s)
        self.assertEqual("sequential", decision.reason)


if __name__ == "__main__":
    unittest.main()
