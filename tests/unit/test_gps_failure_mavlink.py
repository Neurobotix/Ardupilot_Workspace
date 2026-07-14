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
from sim_ard_gaw.campaigns.test_suite.core.models import (  # noqa: E402
    TestCase as _SuiteTestCase,  # aliased so pytest does not try to collect it
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
    GpsInjectionPlan,
    TriggerEvidence,
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
        _fresh_trigger_event(1),
        _fresh_trigger_event(2),
        _fresh_trigger_event(3),
        {
            **_fresh_trigger_event(4),
            "trigger_latitude_deg": trigger_latitude_deg,
            "trigger_time_s": trigger_time_s,
            "elapsed_since_trigger_s": elapsed_since_trigger_s,
        },
    ]


def _fresh_trigger_event(seq: int) -> dict[str, Any]:
    return {
        "seq": seq,
        "armed": True,
        "mode": "AUTO",
        "heartbeat_age_s": 0.1,
        "heartbeat_fresh": True,
        "simstate_age_s": 0.1,
        "simstate_fresh": True,
    }


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


_UNSET = object()


def _case_with_recipe(
    case_id: str,
    *,
    set_fields: dict[str, Any] | None = None,
    drop_fields: tuple[str, ...] = (),
    replace_recipe: Any = _UNSET,
    replace_param: dict[str, Any] | None = None,
    drop_param: tuple[str, ...] = (),
) -> _SuiteTestCase:
    """Return a copy of a generated case with a mutated fault_recipe/params.

    Lets a test build a malformed public ``TestCase`` (missing/invalid recipe
    fields, or a non-mapping recipe/trigger) without editing the case generator.
    """

    base = _case(case_id)
    params = dict(base.parameters)
    if replace_recipe is not _UNSET:
        params["fault_recipe"] = replace_recipe
    else:
        recipe = dict(params.get("fault_recipe") or {})
        for field_name in drop_fields:
            recipe.pop(field_name, None)
        for field_name, value in (set_fields or {}).items():
            recipe[field_name] = value
        params["fault_recipe"] = recipe
    for key, value in (replace_param or {}).items():
        params[key] = value
    for key in drop_param:
        params.pop(key, None)
    return _SuiteTestCase(
        suite_name=base.suite_name,
        case_id=base.case_id,
        parameters=params,
        scenario_name=base.scenario_name,
        stimulus_name=base.stimulus_name,
        mission_file=base.mission_file,
        acceptance_target_runs=base.acceptance_target_runs,
        tags=base.tags,
    )


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

    def test_malformed_rule_objects_fail_closed_with_value_error(self) -> None:
        # Every malformed rule shape must fail closed with ValueError (not a
        # leaked KeyError/TypeError) and perform zero connection calls.
        malformed_rules = [
            {"SIM_GPS1_ENABLE": {"expected": 0.0}},           # missing tolerance
            {"SIM_GPS1_ENABLE": {"tolerance": 0.0}},          # missing expected
            {"SIM_GPS1_ENABLE": 5.0},                         # non-mapping rule
            {"SIM_GPS1_ENABLE": "bad"},                       # non-mapping rule
            {"SIM_GPS1_ENABLE": None},                        # non-mapping rule
        ]
        for rules in malformed_rules:
            with self.subTest(rules=rules):
                fake = _FakeParamConnection()
                with self.assertRaises(ValueError):
                    set_and_read_back_parameters(
                        fake,
                        {"SIM_GPS1_ENABLE": 0.0},
                        readback_rules=rules,
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

    def test_failed_write_reports_parameter_in_missing_only_once(self) -> None:
        # A write that errors must appear exactly once in missing_parameters
        # (not duplicated by both the write-failure list and the readback-missing
        # comparison), with its error reason recorded in tolerance_failures.
        class _FailingWriteConnection(_FakeParamConnection):
            def set_parameter(self, name: str, value: float) -> float:
                raise RuntimeError("transport down")

        result = set_and_read_back_parameters(
            _FailingWriteConnection(),
            {"SIM_GPS1_JAM": 1.0},
        )
        self.assertFalse(result.success)
        self.assertEqual(["SIM_GPS1_JAM"], result.missing_parameters)
        self.assertEqual(
            [("SIM_GPS1_JAM", "transport down")],
            [(f.param, f.reason) for f in result.tolerance_failures],
        )

    def test_failed_read_reports_parameter_in_missing_only_once(self) -> None:
        class _FailingReadConnection(_FakeParamConnection):
            def read_parameter(self, name: str) -> float:
                raise TimeoutError(name)

        rules = readback_rules_for_payload({"SIM_GPS1_JAM": 1.0})
        result = read_back_injected_parameters(_FailingReadConnection(), rules)
        self.assertFalse(result.success)
        self.assertEqual(["SIM_GPS1_JAM"], result.missing_parameters)
        self.assertEqual(
            ["SIM_GPS1_JAM"], [f.param for f in result.tolerance_failures]
        )

    def test_mixed_failed_and_missing_params_deduped_and_sorted(self) -> None:
        # One parameter's read errors (transport failure), the other two succeed.
        # The failing name must appear exactly once, deterministically sorted, and
        # the successful ones must be absent from missing_parameters.
        class _FailOneReadConnection(_FakeParamConnection):
            def read_parameter(self, name: str) -> float:
                if name == "SIM_GPS1_JAM":
                    raise TimeoutError(name)
                return self.values.get(name, 0.0)

        rules = readback_rules_for_payload(
            {"SIM_GPS1_JAM": 1.0, "SIM_GPS1_ENABLE": 0.0, "SIM_GPS1_GLTCH_Y": 0.0}
        )
        result = read_back_injected_parameters(
            _FailOneReadConnection(
                {"SIM_GPS1_ENABLE": 0.0, "SIM_GPS1_GLTCH_Y": 0.0}
            ),
            rules,
        )
        self.assertFalse(result.success)
        self.assertEqual(["SIM_GPS1_JAM"], result.missing_parameters)
        self.assertEqual(
            sorted(set(result.missing_parameters)), result.missing_parameters
        )
        self.assertEqual(1, result.missing_parameters.count("SIM_GPS1_JAM"))


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

    def test_regressive_or_duplicate_trigger_trace_does_not_authorize(self) -> None:
        armed = lambda seq: {"seq": seq, "armed": True, "mode": "AUTO"}
        for trace in (
            [armed(1), armed(2), armed(3), armed(2), armed(4)],  # regression
            [armed(1), armed(3), armed(4)],                       # skip
            [armed(1), armed(2), armed(4)],                       # jump past 3
        ):
            with self.subTest(trace=trace):
                plan = build_authorized_injection_plan(_case("jamming_repeat_01"), trace)
                self.assertFalse(plan.execution_authorized)
                fake = _FakeParamConnection()
                result = execute_injection_plan(plan, fake)
                self.assertFalse(result.success)
                self._assert_no_connection_calls(fake)

    def test_directly_constructed_plan_cannot_forge_authorization(self) -> None:
        # A hand-built plan with a forged TriggerEvidence(validated=True) must not
        # be able to execute a write: authorization requires the internal token
        # AND a replay of a genuinely valid source trace.
        case = _case("jamming_repeat_01")
        forgeries = [
            TriggerEvidence(validated=True, reason="forged"),
            TriggerEvidence(
                validated=True,
                reason="forged",
                source_trace=({"seq": 4, "armed": True, "mode": "AUTO"},),
            ),
        ]
        for evidence in forgeries:
            with self.subTest(evidence=evidence.reason):
                forged = GpsInjectionPlan(
                    case_id=case.case_id,
                    fault_type="jamming",
                    trigger={},
                    trigger_event={},
                    injection_payload={"SIM_GPS1_JAM": 1.0},
                    readback_rules={"SIM_GPS1_JAM": ReadbackRule(1.0, 0.0)},
                    preview_only=False,
                    trigger_evidence=evidence,
                )
                self.assertFalse(forged.execution_authorized)
                fake = _FakeParamConnection()
                result = execute_injection_plan(forged, fake)
                self.assertFalse(result.success)
                self.assertEqual("trigger_authorization_missing", result.reason)
                self._assert_no_connection_calls(fake)

    def test_validated_evidence_reports_authorized_true(self) -> None:
        evidence = validate_trigger_trace(_valid_trace())
        self.assertTrue(evidence.validated)
        self.assertTrue(evidence.is_authorized())
        self.assertTrue(evidence.as_dict()["authorized"])
        # A rejected trace is neither validated nor authorized.
        rejected = validate_trigger_trace(["bad"])
        self.assertFalse(rejected.validated)
        self.assertFalse(rejected.is_authorized())


class GpsFailureMalformedRecipeFailClosedTests(unittest.TestCase):
    """H1: malformed public recipes/triggers must fail closed, never crash.

    A malformed TestCase/recipe/trigger must produce a structured not-ready plan
    (empty payload, empty readback rules, no restore steps, deterministic
    ``plan_resolution_failed`` info) instead of escaping as an uncaught
    KeyError/TypeError, and executing such a plan must make zero connection
    calls.
    """

    def _assert_no_connection_calls(self, fake: _FakeParamConnection) -> None:
        self.assertEqual([], fake.set_order)
        self.assertEqual([], fake.read_order)

    def _assert_structured_failure(self, plan: GpsInjectionPlan) -> None:
        self.assertFalse(plan.ready_to_inject, plan.as_dict())
        self.assertEqual({}, plan.injection_payload)
        self.assertEqual({}, plan.readback_rules)
        self.assertEqual([], plan.restore_plan)
        self.assertFalse(plan.execution_authorized)
        self.assertTrue(plan.failures)
        self.assertEqual("plan_resolution_failed", plan.failures[0]["reason"])
        detail = plan.failures[0]["detail"]
        self.assertIsInstance(detail, str)
        # The message is a deterministic domain string, not raw KeyError repr.
        self.assertNotIn("KeyError", detail)
        self.assertNotIn("'offset_magnitude_m'", detail)
        # The whole plan must remain JSON-safe / NaN-free.
        json.dumps(plan.as_dict(), allow_nan=False)

    def _event(self) -> dict[str, Any]:
        return {"trigger_latitude_deg": 0.0, "trigger_time_s": 100.0}

    def test_step_glitch_missing_offset_magnitude_fails_closed(self) -> None:
        case = _case_with_recipe("step_glitch_100m", drop_fields=("offset_magnitude_m",))
        plan = build_live_injection_plan(case, self._event())
        self._assert_structured_failure(plan)
        self.assertIn("missing required recipe value", plan.failures[0]["detail"])
        self.assertIn("offset_magnitude_m", plan.failures[0]["detail"])

    def test_step_glitch_offset_none_fails_closed(self) -> None:
        case = _case_with_recipe("step_glitch_100m", set_fields={"offset_magnitude_m": None})
        plan = build_live_injection_plan(case, self._event())
        self._assert_structured_failure(plan)
        self.assertIn("must be finite", plan.failures[0]["detail"])

    def test_step_glitch_offset_non_numeric_string_fails_closed(self) -> None:
        case = _case_with_recipe("step_glitch_100m", set_fields={"offset_magnitude_m": "big"})
        plan = build_live_injection_plan(case, self._event())
        self._assert_structured_failure(plan)
        self.assertIn("must be finite", plan.failures[0]["detail"])

    def test_step_glitch_offset_nan_and_infinities_fail_closed(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                case = _case_with_recipe(
                    "step_glitch_100m", set_fields={"offset_magnitude_m": value}
                )
                plan = build_live_injection_plan(case, self._event())
                self._assert_structured_failure(plan)
                self.assertIn("must be finite", plan.failures[0]["detail"])

    def test_fault_recipe_as_list_string_number_fails_closed(self) -> None:
        for recipe in ([1, 2, 3], "not-a-recipe", 5):
            with self.subTest(recipe=recipe):
                case = _case_with_recipe("step_glitch_100m", replace_recipe=recipe)
                plan = build_live_injection_plan(case, self._event())
                self._assert_structured_failure(plan)
                self.assertIn("fault_recipe must be a mapping", plan.failures[0]["detail"])

    def test_malformed_trigger_in_case_parameters_fails_closed(self) -> None:
        for trigger in (["a", "b"], "trig", 7):
            with self.subTest(trigger=trigger):
                case = _case_with_recipe(
                    "step_glitch_100m", replace_param={"trigger": trigger}
                )
                plan = build_live_injection_plan(case, self._event())
                self._assert_structured_failure(plan)
                self.assertIn("trigger must be a mapping", plan.failures[0]["detail"])

    def test_missing_or_empty_trigger_metadata_for_fault_case_fails_closed(self) -> None:
        # A fault-writing case MUST carry the populated ADR-0020 trigger. A
        # None / missing / empty trigger is malformed public input: preview and
        # authorized plans must fail closed and execute zero connection calls.
        fault_case_ids = (
            "step_glitch_100m",
            "slow_drift_0p5_mps",
            "hard_denial_15s",
            "jamming_repeat_01",
        )
        # (label, kwargs to _case_with_recipe) for each malformed trigger shape.
        malformations = (
            ("none", {"replace_param": {"trigger": None}}),
            ("empty", {"replace_param": {"trigger": {}}}),
            ("missing", {"drop_param": ("trigger",)}),
        )
        for case_id in fault_case_ids:
            for label, kwargs in malformations:
                with self.subTest(case_id=case_id, trigger=label):
                    case = _case_with_recipe(case_id, **kwargs)  # type: ignore[arg-type]
                    preview = build_live_injection_plan(case, self._event())
                    self._assert_structured_failure(preview)
                    self.assertIn(
                        "missing required trigger metadata for fault case",
                        preview.failures[0]["detail"],
                    )
                    # A genuinely valid monitor trace must NOT rescue a malformed
                    # case: the plan still fails closed and writes nothing.
                    authorized = build_authorized_injection_plan(case, _valid_trace())
                    self._assert_structured_failure(authorized)
                    fake = _FakeParamConnection()
                    result = execute_injection_plan(authorized, fake)
                    self.assertFalse(result.success)
                    self._assert_no_connection_calls(fake)

    def test_missing_trigger_metadata_for_nominal_case_stays_ready(self) -> None:
        # Nominal is a no-write case and does not require trigger metadata.
        case = _case_with_recipe("nominal", drop_param=("trigger",))
        plan = build_live_injection_plan(case, {})
        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertEqual({}, plan.injection_payload)
        self.assertFalse(plan.requires_trigger_authorization)
        self.assertTrue(plan.execution_authorized)

    def test_malformed_trigger_event_fails_closed(self) -> None:
        for event in ([("trigger_latitude_deg", 0.0)], "event", 3):
            with self.subTest(event=event):
                plan = build_live_injection_plan(_case("step_glitch_100m"), event)  # type: ignore[arg-type]
                self._assert_structured_failure(plan)
                self.assertIn("trigger_event must be a mapping", plan.failures[0]["detail"])

    def test_preview_builder_returns_structured_failure(self) -> None:
        case = _case_with_recipe("step_glitch_100m", drop_fields=("offset_magnitude_m",))
        plan = build_live_injection_plan(case, self._event())
        self.assertTrue(plan.preview_only)
        self._assert_structured_failure(plan)

    def test_authorized_builder_returns_structured_failure_after_valid_trace(self) -> None:
        case = _case_with_recipe("step_glitch_100m", drop_fields=("offset_magnitude_m",))
        plan = build_authorized_injection_plan(case, _valid_trace())
        # The trigger trace itself was valid ...
        self.assertIsNotNone(plan.trigger_evidence)
        assert plan.trigger_evidence is not None
        self.assertTrue(plan.trigger_evidence.validated)
        # ... but the malformed recipe still fails plan resolution closed.
        self.assertFalse(plan.preview_only)
        self._assert_structured_failure(plan)

    def test_failed_plan_execution_makes_zero_connection_calls(self) -> None:
        case = _case_with_recipe("step_glitch_100m", drop_fields=("offset_magnitude_m",))
        for plan in (
            build_live_injection_plan(case, self._event()),
            build_authorized_injection_plan(case, _valid_trace()),
        ):
            with self.subTest(preview_only=plan.preview_only):
                fake = _FakeParamConnection()
                result = execute_injection_plan(plan, fake)
                self.assertFalse(result.success)
                self._assert_no_connection_calls(fake)

    def test_valid_step_glitch_output_remains_correct(self) -> None:
        plan = build_live_injection_plan(_case("step_glitch_100m"), self._event())
        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertEqual(glitch.step_glitch_payload(100.0, 0.0), plan.injection_payload)
        self.assertEqual(set(plan.injection_payload), set(plan.readback_rules))

    def test_valid_slow_drift_output_remains_correct(self) -> None:
        plan = build_live_injection_plan(
            _case("slow_drift_0p5_mps"),
            {
                "trigger_latitude_deg": 0.0,
                "trigger_time_s": 100.0,
                "elapsed_since_trigger_s": 90.0,
            },
        )
        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertEqual(glitch.slow_drift_payload(0.5, 90.0, 0.0), plan.injection_payload)

    def test_valid_denial_and_jamming_restore_behavior_remains_correct(self) -> None:
        denial = build_live_injection_plan(_case("hard_denial_15s"), {})
        self.assertTrue(denial.ready_to_inject, denial.as_dict())
        self.assertEqual({"SIM_GPS1_ENABLE": 0.0}, denial.injection_payload)
        self.assertEqual(1, len(denial.restore_plan))
        self.assertEqual({"SIM_GPS1_ENABLE": 1.0}, denial.restore_plan[0].payload)

        jamming = build_live_injection_plan(_case("jamming_repeat_01"), {})
        self.assertTrue(jamming.ready_to_inject, jamming.as_dict())
        self.assertEqual({"SIM_GPS1_JAM": 1.0}, jamming.injection_payload)
        self.assertEqual(1, len(jamming.restore_plan))
        self.assertEqual({"SIM_GPS1_JAM": 0.0}, jamming.restore_plan[0].payload)

    def test_optional_restore_duration_absent_means_no_restore_step(self) -> None:
        # Missing optional denial duration keeps the documented "no restore step"
        # semantics rather than raising or forcing a required field.
        case = _case_with_recipe("hard_denial_15s", drop_fields=("denial_duration_s",))
        plan = build_live_injection_plan(case, {})
        self.assertTrue(plan.ready_to_inject, plan.as_dict())
        self.assertEqual({"SIM_GPS1_ENABLE": 0.0}, plan.injection_payload)
        self.assertEqual([], plan.restore_plan)

    def test_authorized_builder_with_bad_trigger_and_invalid_trace_fails_closed(self) -> None:
        # The not-validated return path must not crash on a malformed `trigger`
        # when the trace is also invalid; it normalizes fail-closed to {}.
        case = _case_with_recipe("step_glitch_100m", replace_param={"trigger": "bad"})
        plan = build_authorized_injection_plan(case, ["invalid-trace"])
        self.assertFalse(plan.ready_to_inject, plan.as_dict())
        self.assertEqual({}, plan.trigger)
        self.assertEqual({}, plan.injection_payload)
        self.assertFalse(plan.execution_authorized)
        self.assertEqual("trigger_not_validated", plan.failures[0]["reason"])
        json.dumps(plan.as_dict(), allow_nan=False)
        fake = _FakeParamConnection()
        result = execute_injection_plan(plan, fake)
        self.assertFalse(result.success)
        self._assert_no_connection_calls(fake)

    def test_unsupported_fault_type_still_fails_closed(self) -> None:
        case = _case_with_recipe(
            "step_glitch_100m", replace_param={"fault_type": "meteor_strike"}
        )
        plan = build_live_injection_plan(case, self._event())
        self._assert_structured_failure(plan)
        self.assertIn("Unsupported gps_failure fault_type", plan.failures[0]["detail"])


if __name__ == "__main__":
    unittest.main()
