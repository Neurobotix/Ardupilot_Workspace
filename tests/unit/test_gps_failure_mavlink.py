from __future__ import annotations

import importlib.abc
import json
import math
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure import glitch  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.case_generator import (  # noqa: E402
    GpsFailureCaseGenerator,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.config import (  # noqa: E402
    GpsFailureConfig,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.mavlink import (  # noqa: E402
    ReadbackRule,
    compare_readbacks,
    preflight_batch,
    read_back_injected_parameters,
    read_one_parameter,
    readback_rules_for_payload,
    set_and_read_back_parameters,
    set_many_parameters,
    set_one_parameter,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.runtime import (  # noqa: E402
    build_authorized_injection_plan,
    build_live_injection_plan,
    execute_injection_plan,
    validate_trigger_trace,
)


def _valid_trace(
    *,
    trigger_latitude_deg: float = 0.0,
    trigger_time_s: float = 100.0,
    elapsed_since_trigger_s: float = 90.0,
) -> list[dict[str, Any]]:
    """A minimal armed/AUTO seq 1->2->3->4 monitor trace that authorizes a plan."""
    return [
        {"seq": 1, "armed": True, "mode": "AUTO"},
        {"seq": 2, "armed": True, "mode": "AUTO"},
        {"seq": 3, "armed": True, "mode": "AUTO"},
        {
            "seq": 4,
            "armed": True,
            "mode": "AUTO",
            "trigger_latitude_deg": trigger_latitude_deg,
            "trigger_time_s": trigger_time_s,
            "elapsed_since_trigger_s": elapsed_since_trigger_s,
        },
    ]


class _FakeParamConnection:
    def __init__(self, values: dict[str, float] | None = None) -> None:
        self.values = dict(values or {})
        self.set_order: list[tuple[str, float]] = []
        self.read_order: list[str] = []

    def set_parameter(self, name: str, value: float) -> float:
        self.set_order.append((name, value))
        self.values[name] = value
        return self.values[name]

    def read_parameter(self, name: str) -> float:
        self.read_order.append(name)
        if name not in self.values:
            raise TimeoutError(name)
        return self.values[name]

    def param_fetch_one(self, name: str) -> None:
        self.read_order.append(name)

    def param_set_send(self, name: str, value: float) -> None:
        self.set_order.append((name, value))
        self.values[name] = value

    def recv_match(self, **_kwargs: Any) -> Any:
        return None


def _case(case_id: str):
    return GpsFailureCaseGenerator(GpsFailureConfig()).get_case(case_id)


class GpsFailureMavlinkHelperTests(unittest.TestCase):
    def test_set_and_read_one_parameter_succeeds_with_fake_connection(self) -> None:
        fake = _FakeParamConnection()
        write = set_one_parameter(fake, "SIM_GPS1_JAM", 1.0)
        read = read_one_parameter(fake, "SIM_GPS1_JAM")

        self.assertTrue(write.ok)
        self.assertEqual("SIM_GPS1_JAM", write.param)
        self.assertEqual(1.0, write.requested_value)
        self.assertEqual(1.0, write.observed_value)
        self.assertTrue(read.ok)
        self.assertEqual(1.0, read.value)

    def test_set_many_parameters_preserves_sorted_deterministic_order(self) -> None:
        fake = _FakeParamConnection()
        writes = set_many_parameters(
            fake,
            {
                "SIM_GPS1_JAM": 1.0,
                "SIM_GPS1_ENABLE": 0.0,
                "SIM_GPS1_GLTCH_Y": 0.25,
            },
        )

        self.assertEqual(
            ["SIM_GPS1_ENABLE", "SIM_GPS1_GLTCH_Y", "SIM_GPS1_JAM"],
            [write.param for write in writes],
        )
        self.assertEqual(
            [
                ("SIM_GPS1_ENABLE", 0.0),
                ("SIM_GPS1_GLTCH_Y", 0.25),
                ("SIM_GPS1_JAM", 1.0),
            ],
            fake.set_order,
        )

    def test_readback_success_within_tolerance(self) -> None:
        rules = readback_rules_for_payload({"SIM_GPS1_GLTCH_Y": 1.0e-6})
        result = compare_readbacks(rules, {"SIM_GPS1_GLTCH_Y": 1.0005e-6})

        self.assertTrue(result.success, result.as_dict())
        self.assertEqual([], result.missing_parameters)
        self.assertEqual([], result.tolerance_failures)

    def test_readback_failure_when_missing(self) -> None:
        rules = readback_rules_for_payload({"SIM_GPS1_ENABLE": 0.0})
        result = compare_readbacks(rules, {})

        self.assertFalse(result.success)
        self.assertEqual(["SIM_GPS1_ENABLE"], result.missing_parameters)

    def test_readback_failure_when_out_of_tolerance(self) -> None:
        rules = readback_rules_for_payload({"SIM_GPS1_ENABLE": 0.0})
        result = compare_readbacks(rules, {"SIM_GPS1_ENABLE": 1.0})

        self.assertFalse(result.success)
        self.assertEqual("out_of_tolerance", result.tolerance_failures[0].reason)
        self.assertEqual("SIM_GPS1_ENABLE", result.tolerance_failures[0].param)

    def test_readback_failure_on_nan_and_infinity(self) -> None:
        rules = readback_rules_for_payload({"SIM_GPS1_JAM": 1.0})
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                result = compare_readbacks(rules, {"SIM_GPS1_JAM": value})
                self.assertFalse(result.success)
                self.assertEqual("non_finite", result.tolerance_failures[0].reason)

    def test_write_rejects_nan_and_infinity_before_connection_call(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                fake = _FakeParamConnection()
                with self.assertRaisesRegex(ValueError, "requested must be finite"):
                    set_one_parameter(fake, "SIM_GPS1_JAM", value)
                self.assertEqual([], fake.set_order)

    def test_read_back_injected_parameters_reports_missing_fake_param(self) -> None:
        rules = readback_rules_for_payload({"SIM_GPS1_JAM": 1.0})
        result = read_back_injected_parameters(_FakeParamConnection(), rules)

        self.assertFalse(result.success)
        self.assertIn("SIM_GPS1_JAM", result.missing_parameters)

    def test_set_and_read_back_parameters_returns_structured_success(self) -> None:
        result = set_and_read_back_parameters(
            _FakeParamConnection(),
            {"SIM_GPS1_ENABLE": 0.0},
        )

        self.assertTrue(result.success, result.as_dict())
        self.assertEqual(1, len(result.writes_attempted))
        self.assertEqual({"SIM_GPS1_ENABLE": 0.0}, result.readbacks_observed)

    def test_import_does_not_require_real_mavlink_dependency(self) -> None:
        blocked = {"pymavlink", "pymavlink.mavutil"}

        class BlockMavlink(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname in blocked:
                    raise AssertionError(f"blocked import: {fullname}")
                return None

        finder = BlockMavlink()
        sys.meta_path.insert(0, finder)
        try:
            __import__("sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.mavlink")
            __import__("sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.runtime")
        finally:
            sys.meta_path.remove(finder)


class GpsFailureBatchPreflightTests(unittest.TestCase):
    """Blocker 6: batch validation is atomic and precedes any connection call."""

    def _assert_no_connection_calls(self, fake: _FakeParamConnection) -> None:
        self.assertEqual([], fake.set_order)
        self.assertEqual([], fake.read_order)

    def test_invalid_entry_sorted_after_valid_entry_writes_nothing(self) -> None:
        fake = _FakeParamConnection()
        with self.assertRaisesRegex(ValueError, "must be finite"):
            set_and_read_back_parameters(
                fake,
                {"SIM_GPS1_ENABLE": 0.0, "SIM_GPS1_JAM": float("inf")},
            )
        self._assert_no_connection_calls(fake)

    def test_nan_and_infinities_write_nothing(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                fake = _FakeParamConnection()
                with self.assertRaisesRegex(ValueError, "must be finite"):
                    set_and_read_back_parameters(
                        fake,
                        {"SIM_GPS1_ENABLE": 0.0, "SIM_GPS1_JAM": value},
                    )
                self._assert_no_connection_calls(fake)

    def test_unknown_parameter_after_valid_parameter_writes_nothing(self) -> None:
        fake = _FakeParamConnection()
        with self.assertRaisesRegex(ValueError, "Unknown SIM_GPS parameter"):
            set_and_read_back_parameters(
                fake,
                {"SIM_GPS1_ENABLE": 0.0, "SIM_GPS1_ZZZ_UNKNOWN": 1.0},
            )
        self._assert_no_connection_calls(fake)

    def test_invalid_readback_rule_after_valid_rule_writes_nothing(self) -> None:
        fake = _FakeParamConnection()
        with self.assertRaisesRegex(ValueError, "must be finite"):
            set_and_read_back_parameters(
                fake,
                {"SIM_GPS1_ENABLE": 0.0, "SIM_GPS1_JAM": 1.0},
                readback_rules={
                    "SIM_GPS1_ENABLE": ReadbackRule(expected=0.0, tolerance=0.0),
                    "SIM_GPS1_JAM": {"expected": float("inf"), "tolerance": 0.0},
                },
            )
        self._assert_no_connection_calls(fake)

    def test_missing_rule_for_one_payload_parameter_writes_nothing(self) -> None:
        fake = _FakeParamConnection()
        with self.assertRaisesRegex(ValueError, "missing readback rule"):
            set_and_read_back_parameters(
                fake,
                {"SIM_GPS1_ENABLE": 0.0, "SIM_GPS1_JAM": 1.0},
                readback_rules={"SIM_GPS1_ENABLE": ReadbackRule(0.0, 0.0)},
            )
        self._assert_no_connection_calls(fake)

    def test_extra_rule_key_writes_nothing(self) -> None:
        fake = _FakeParamConnection()
        with self.assertRaisesRegex(ValueError, "absent from the payload"):
            set_and_read_back_parameters(
                fake,
                {"SIM_GPS1_ENABLE": 0.0},
                readback_rules={
                    "SIM_GPS1_ENABLE": ReadbackRule(0.0, 0.0),
                    "SIM_GPS1_JAM": ReadbackRule(1.0, 0.0),
                },
            )
        self._assert_no_connection_calls(fake)

    def test_negative_and_non_finite_tolerance_write_nothing(self) -> None:
        for tolerance in (-0.1, math.inf, math.nan):
            with self.subTest(tolerance=tolerance):
                fake = _FakeParamConnection()
                with self.assertRaises(ValueError):
                    set_and_read_back_parameters(
                        fake,
                        {"SIM_GPS1_ENABLE": 0.0},
                        readback_rules={
                            "SIM_GPS1_ENABLE": {"expected": 0.0, "tolerance": tolerance}
                        },
                    )
                self._assert_no_connection_calls(fake)

    def test_malformed_rule_mapping_writes_nothing(self) -> None:
        fake = _FakeParamConnection()
        with self.assertRaises((ValueError, KeyError, TypeError)):
            set_and_read_back_parameters(
                fake,
                {"SIM_GPS1_ENABLE": 0.0},
                readback_rules={"SIM_GPS1_ENABLE": {"expected": 0.0}},
            )
        self._assert_no_connection_calls(fake)

    def test_non_mapping_payload_writes_nothing(self) -> None:
        fake = _FakeParamConnection()
        with self.assertRaisesRegex(ValueError, "payload must be a mapping"):
            set_and_read_back_parameters(fake, [("SIM_GPS1_ENABLE", 0.0)])  # type: ignore[arg-type]
        self._assert_no_connection_calls(fake)

    def test_valid_batch_retains_sorted_deterministic_order(self) -> None:
        fake = _FakeParamConnection()
        result = set_and_read_back_parameters(
            fake,
            {"SIM_GPS1_JAM": 1.0, "SIM_GPS1_ENABLE": 0.0, "SIM_GPS1_GLTCH_Y": 0.25},
        )
        self.assertTrue(result.success, result.as_dict())
        self.assertEqual(
            ["SIM_GPS1_ENABLE", "SIM_GPS1_GLTCH_Y", "SIM_GPS1_JAM"],
            [name for name, _ in fake.set_order],
        )

    def test_valid_write_and_readback_success_is_unchanged(self) -> None:
        result = set_and_read_back_parameters(
            _FakeParamConnection(),
            {"SIM_GPS1_ENABLE": 0.0},
        )
        self.assertTrue(result.success, result.as_dict())
        self.assertEqual({"SIM_GPS1_ENABLE": 0.0}, result.readbacks_observed)
        self.assertEqual([], result.tolerance_failures)
        self.assertEqual([], result.missing_parameters)

    def test_failed_transport_after_validation_is_fail_closed(self) -> None:
        class _FailingWriteConnection(_FakeParamConnection):
            def set_parameter(self, name: str, value: float) -> float:
                raise RuntimeError("transport down")

        result = set_and_read_back_parameters(
            _FailingWriteConnection(),
            {"SIM_GPS1_ENABLE": 0.0},
        )
        self.assertFalse(result.success)
        self.assertIn("SIM_GPS1_ENABLE", result.missing_parameters)

    def test_preflight_batch_returns_validated_pair_without_connection(self) -> None:
        payload, rules = preflight_batch({"SIM_GPS1_JAM": 1.0}, None)
        self.assertEqual({"SIM_GPS1_JAM": 1.0}, payload)
        self.assertEqual({"SIM_GPS1_JAM"}, set(rules))


class GpsFailureRuntimePlanTests(unittest.TestCase):
    def test_nominal_produces_no_writes_and_no_launch(self) -> None:
        plan = build_live_injection_plan(_case("nominal"), {})

        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertEqual({}, plan.injection_payload)
        self.assertEqual({}, plan.readback_rules)
        self.assertEqual([], plan.restore_plan)
        self.assertFalse(plan.launch_performed)
        self.assertFalse(plan.live_readback_performed)

    def test_slow_drift_resolves_trigger_latitude_and_elapsed_time_to_degrees(self) -> None:
        plan = build_live_injection_plan(
            _case("slow_drift_0p5_mps"),
            {
                "trigger_latitude_deg": 0.0,
                "trigger_time_s": 100.0,
                "elapsed_since_trigger_s": 90.0,
            },
        )

        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertEqual(
            glitch.slow_drift_payload(0.5, 90.0, 0.0),
            plan.injection_payload,
        )
        self.assertEqual(set(plan.injection_payload), set(plan.readback_rules))
        self.assertFalse(plan.launch_performed)

    def test_step_glitch_resolves_offset_to_degree_payload(self) -> None:
        plan = build_live_injection_plan(
            _case("step_glitch_100m"),
            {"trigger_latitude_deg": 0.0, "trigger_time_s": 100.0},
        )

        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertEqual(glitch.step_glitch_payload(100.0, 0.0), plan.injection_payload)
        self.assertAlmostEqual(
            100.0 / 111_320.0,
            plan.injection_payload["SIM_GPS1_GLTCH_Y"],
            places=12,
        )

    def test_hard_denial_produces_enable_zero_and_restore_plan(self) -> None:
        plan = build_live_injection_plan(_case("hard_denial_15s"), {})

        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertEqual({"SIM_GPS1_ENABLE": 0.0}, plan.injection_payload)
        self.assertEqual({"SIM_GPS1_ENABLE"}, set(plan.readback_rules))
        self.assertEqual(1, len(plan.restore_plan))
        self.assertEqual(15.0, plan.restore_plan[0].elapsed_since_trigger_s)
        self.assertEqual({"SIM_GPS1_ENABLE": 1.0}, plan.restore_plan[0].payload)
        self.assertEqual({"SIM_GPS1_ENABLE"}, set(plan.restore_plan[0].readback_rules))

    def test_jamming_produces_jam_one_and_restore_plan(self) -> None:
        plan = build_live_injection_plan(_case("jamming_repeat_01"), {})

        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertEqual({"SIM_GPS1_JAM": 1.0}, plan.injection_payload)
        self.assertEqual(1, len(plan.restore_plan))
        self.assertEqual(45.0, plan.restore_plan[0].elapsed_since_trigger_s)
        self.assertEqual({"SIM_GPS1_JAM": 0.0}, plan.restore_plan[0].payload)

    def test_missing_trigger_latitude_for_glitch_fault_fails_closed(self) -> None:
        plan = build_live_injection_plan(
            _case("step_glitch_100m"),
            {"trigger_time_s": 10.0},
        )

        self.assertFalse(plan.ready_to_inject)
        self.assertEqual({}, plan.injection_payload)
        self.assertIn("missing required trigger event value", plan.failures[0]["detail"])

    def test_missing_elapsed_time_for_slow_drift_fails_closed(self) -> None:
        plan = build_live_injection_plan(
            _case("slow_drift_0p5_mps"),
            {"trigger_latitude_deg": 0.0, "trigger_time_s": 10.0},
        )

        self.assertFalse(plan.ready_to_inject)
        self.assertEqual({}, plan.readback_rules)
        self.assertIn("elapsed_since_trigger_s", plan.failures[0]["detail"])

    def test_non_finite_latitude_and_time_fail_closed(self) -> None:
        cases = [
            (
                _case("step_glitch_100m"),
                {"trigger_latitude_deg": math.nan, "trigger_time_s": 10.0},
                "trigger_latitude_deg must be finite",
            ),
            (
                _case("slow_drift_0p5_mps"),
                {
                    "trigger_latitude_deg": 0.0,
                    "trigger_time_s": 10.0,
                    "elapsed_since_trigger_s": math.inf,
                },
                "elapsed_since_trigger_s must be finite",
            ),
            (
                _case("jamming_repeat_01"),
                {"trigger_time_s": math.nan},
                "trigger_time_s must be finite",
            ),
        ]
        for case, event, expected in cases:
            with self.subTest(case=case.case_id):
                plan = build_live_injection_plan(case, event)
                self.assertFalse(plan.ready_to_inject)
                self.assertIn(expected, plan.failures[0]["detail"])

    def test_every_injected_and_restore_param_has_readback_rule(self) -> None:
        case_ids = [
            "slow_drift_0p5_mps",
            "step_glitch_050m",
            "hard_denial_05s",
            "jamming_repeat_01",
        ]
        for case_id in case_ids:
            with self.subTest(case_id=case_id):
                plan = build_live_injection_plan(
                    _case(case_id),
                    {
                        "trigger_latitude_deg": 0.0,
                        "trigger_time_s": 10.0,
                        "elapsed_since_trigger_s": 90.0,
                    },
                )
                self.assertTrue(plan.ready_to_inject, plan.as_dict())
                self.assertEqual(set(plan.injection_payload), set(plan.readback_rules))
                for restore in plan.restore_plan:
                    self.assertEqual(set(restore.payload), set(restore.readback_rules))

    def test_execute_plan_fails_closed_without_live_dependency(self) -> None:
        plan = build_authorized_injection_plan(_case("jamming_repeat_01"), _valid_trace())
        result = execute_injection_plan(plan, None)

        self.assertFalse(result.success)
        self.assertEqual("mavlink_connection_unavailable", result.reason)
        self.assertFalse(result.launch_performed)
        self.assertFalse(result.live_readback_performed)

    def test_execute_authorized_plan_uses_fake_connection_only(self) -> None:
        plan = build_authorized_injection_plan(_case("jamming_repeat_01"), _valid_trace())
        result = execute_injection_plan(plan, _FakeParamConnection())

        self.assertTrue(result.success, result.as_dict())
        self.assertEqual("injection_readback_ok", result.reason)
        self.assertTrue(result.live_readback_performed)
        self.assertFalse(result.launch_performed)


class GpsFailureTriggerAuthorizationTests(unittest.TestCase):
    """Blocker 2: only a validated trigger trace authorizes an executable plan."""

    def _assert_no_connection_calls(self, fake: _FakeParamConnection) -> None:
        self.assertEqual([], fake.set_order)
        self.assertEqual([], fake.read_order)

    def test_empty_trigger_event_for_jamming_is_not_executable(self) -> None:
        plan = build_live_injection_plan(_case("jamming_repeat_01"), {})
        self.assertTrue(plan.preview_only)
        self.assertTrue(plan.requires_trigger_authorization)
        self.assertFalse(plan.execution_authorized)
        fake = _FakeParamConnection()
        result = execute_injection_plan(plan, fake)
        self.assertFalse(result.success)
        self.assertEqual("trigger_authorization_missing", result.reason)
        self._assert_no_connection_calls(fake)

    def test_empty_trigger_event_for_hard_denial_is_not_executable(self) -> None:
        plan = build_live_injection_plan(_case("hard_denial_15s"), {})
        self.assertFalse(plan.execution_authorized)
        fake = _FakeParamConnection()
        result = execute_injection_plan(plan, fake)
        self.assertFalse(result.success)
        self.assertEqual("trigger_authorization_missing", result.reason)
        self._assert_no_connection_calls(fake)

    def test_seq4_before_all_front_half_is_rejected(self) -> None:
        trace = [
            {"seq": 4, "armed": True, "mode": "AUTO"},
            {"seq": 1, "armed": True, "mode": "AUTO"},
            {"seq": 2, "armed": True, "mode": "AUTO"},
            {"seq": 3, "armed": True, "mode": "AUTO"},
        ]
        plan = build_authorized_injection_plan(_case("jamming_repeat_01"), trace)
        self.assertFalse(plan.ready_to_inject)
        self.assertFalse(plan.execution_authorized)
        self.assertIsNotNone(plan.trigger_evidence)
        assert plan.trigger_evidence is not None
        self.assertEqual("trigger_precondition_not_met", plan.trigger_evidence.reason)

    def test_correct_sequences_but_unarmed_is_rejected(self) -> None:
        trace = [
            {"seq": 1, "armed": False, "mode": "AUTO"},
            {"seq": 2, "armed": True, "mode": "AUTO"},
            {"seq": 3, "armed": True, "mode": "AUTO"},
            {"seq": 4, "armed": True, "mode": "AUTO"},
        ]
        plan = build_authorized_injection_plan(_case("jamming_repeat_01"), trace)
        self.assertFalse(plan.execution_authorized)

    def test_correct_sequences_but_wrong_mode_is_rejected(self) -> None:
        trace = [
            {"seq": 1, "armed": True, "mode": "AUTO"},
            {"seq": 2, "armed": True, "mode": "MANUAL"},
            {"seq": 3, "armed": True, "mode": "AUTO"},
            {"seq": 4, "armed": True, "mode": "AUTO"},
        ]
        plan = build_authorized_injection_plan(_case("jamming_repeat_01"), trace)
        self.assertFalse(plan.execution_authorized)

    def test_malformed_trigger_records_are_rejected_without_raising(self) -> None:
        for trace in (["bad"], [{}], [{"seq": "x", "armed": True, "mode": "AUTO"}], [], None):
            with self.subTest(trace=trace):
                evidence = validate_trigger_trace(trace)
                self.assertFalse(evidence.validated)
                plan = build_authorized_injection_plan(_case("jamming_repeat_01"), trace)
                self.assertFalse(plan.execution_authorized)

    def test_valid_armed_auto_trace_is_executable(self) -> None:
        plan = build_authorized_injection_plan(_case("jamming_repeat_01"), _valid_trace())
        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertFalse(plan.preview_only)
        self.assertTrue(plan.execution_authorized)
        assert plan.trigger_evidence is not None
        self.assertTrue(plan.trigger_evidence.validated)
        fake = _FakeParamConnection()
        result = execute_injection_plan(plan, fake)
        self.assertTrue(result.success, result.as_dict())
        self.assertEqual([("SIM_GPS1_JAM", 1.0)], fake.set_order)

    def test_valid_trace_resolves_glitch_payload_for_executable_plan(self) -> None:
        plan = build_authorized_injection_plan(
            _case("slow_drift_0p5_mps"),
            _valid_trace(trigger_latitude_deg=0.0, elapsed_since_trigger_s=90.0),
        )
        self.assertTrue(plan.execution_authorized)
        self.assertEqual(
            glitch.slow_drift_payload(0.5, 90.0, 0.0),
            plan.injection_payload,
        )

    def test_preview_step_glitch_and_slow_drift_cannot_execute(self) -> None:
        for case_id in ("step_glitch_100m", "slow_drift_0p5_mps"):
            with self.subTest(case_id=case_id):
                plan = build_live_injection_plan(
                    _case(case_id),
                    {
                        "trigger_latitude_deg": 0.0,
                        "trigger_time_s": 10.0,
                        "elapsed_since_trigger_s": 90.0,
                    },
                )
                # Preview resolves a payload for inspection ...
                self.assertTrue(plan.injection_payload)
                self.assertTrue(plan.preview_only)
                # ... but is never execution-authorized.
                self.assertFalse(plan.execution_authorized)
                fake = _FakeParamConnection()
                result = execute_injection_plan(plan, fake)
                self.assertFalse(result.success)
                self.assertEqual("trigger_authorization_missing", result.reason)
                self._assert_no_connection_calls(fake)

    def test_rejected_plan_makes_zero_parameter_calls(self) -> None:
        plan = build_authorized_injection_plan(_case("hard_denial_15s"), ["bad"])
        fake = _FakeParamConnection()
        result = execute_injection_plan(plan, fake)
        self.assertFalse(result.success)
        self._assert_no_connection_calls(fake)

    def test_trigger_evidence_is_json_safe(self) -> None:
        plan = build_authorized_injection_plan(_case("jamming_repeat_01"), _valid_trace())
        encoded = json.dumps(plan.as_dict()["trigger_evidence"], allow_nan=False)
        self.assertIn("validated_seq4_edge_armed_auto", encoded)

    def test_nominal_plan_stays_executable_without_a_trigger(self) -> None:
        plan = build_live_injection_plan(_case("nominal"), {})
        self.assertFalse(plan.requires_trigger_authorization)
        self.assertTrue(plan.execution_authorized)
        result = execute_injection_plan(plan, None)
        self.assertTrue(result.success)
        self.assertEqual("no_injection_writes", result.reason)


if __name__ == "__main__":
    unittest.main()
