from __future__ import annotations

import json
import math
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.analyzers import (  # noqa: E402
    classify_observation,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.mechanism_gate import (  # noqa: E402
    GATE_BOUNDARY,
    MECHANISM_STATES,
    evaluate_mechanism_records,
)


def _records(*ratios: float) -> list[dict[str, float]]:
    return [
        {"time_s": float(index), "posTestRatio": ratio}
        for index, ratio in enumerate(ratios)
    ]


class GpsMechanismGateTests(unittest.TestCase):
    def test_all_samples_below_gate_are_fused(self) -> None:
        result = evaluate_mechanism_records(_records(0.1, 0.4, 0.99))

        self.assertEqual("fused_below_gate", result.mechanism_state)
        self.assertTrue(result.accepted_evidence)
        self.assertFalse(result.incomplete)
        self.assertEqual("all_pos_test_ratio_samples_below_gate", result.reason)
        self.assertFalse(result.metrics["crossed_gate"])
        self.assertEqual(["posTestRatio"], result.source_fields["pos_test_ratio"])

    def test_exactly_one_counts_as_crossing_and_rejection(self) -> None:
        result = evaluate_mechanism_records(_records(0.2, 1.0, 0.8))

        self.assertEqual("rejected_above_gate", result.mechanism_state)
        self.assertTrue(result.metrics["crossed_gate"])
        self.assertEqual(1.0, result.metrics["first_crossing_time_s"])
        self.assertEqual(GATE_BOUNDARY, result.metrics["gate_boundary"])

    def test_above_gate_counts_as_crossing_and_rejection(self) -> None:
        result = evaluate_mechanism_records(_records(0.2, 1.01))

        self.assertEqual("rejected_above_gate", result.mechanism_state)
        self.assertTrue(result.metrics["sampled_rejection"])
        self.assertEqual(1, result.metrics["crossing_sample_count"])

    def test_reset_flag_takes_distinct_state_while_preserving_crossing_metrics(self) -> None:
        result = evaluate_mechanism_records(
            [
                {"time_s": 10.0, "posTestRatio": 0.8},
                {"time_s": 11.0, "posTestRatio": 1.3, "reset_event": True},
            ]
        )

        self.assertEqual("reset_detected", result.mechanism_state)
        self.assertTrue(result.metrics["reset_evidence"])
        self.assertTrue(result.metrics["crossed_gate"])
        self.assertEqual(11.0, result.metrics["first_crossing_time_s"])

    def test_empty_records_are_unverified(self) -> None:
        result = evaluate_mechanism_records([])

        self.assertEqual("mechanism_unverified", result.mechanism_state)
        self.assertFalse(result.accepted_evidence)
        self.assertTrue(result.incomplete)
        self.assertEqual("empty_records", result.reason)

    def test_missing_pos_test_ratio_is_unverified(self) -> None:
        result = evaluate_mechanism_records([{"time_s": 0.0}])

        self.assertEqual("mechanism_unverified", result.mechanism_state)
        self.assertEqual("missing_pos_test_ratio", result.reason)
        self.assertEqual(0, result.metrics["invalid_record_index"])

    def test_nan_and_infinity_are_unverified_deterministically(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                result = evaluate_mechanism_records(
                    [{"time_s": 0.0, "posTestRatio": value}]
                )
                self.assertEqual("mechanism_unverified", result.mechanism_state)
                self.assertEqual("invalid_pos_test_ratio", result.reason)

    def test_non_numeric_pos_test_ratio_fails_closed(self) -> None:
        result = evaluate_mechanism_records([{"time_s": 0.0, "posTestRatio": "bad"}])

        self.assertEqual("mechanism_unverified", result.mechanism_state)
        self.assertFalse(result.accepted_evidence)
        self.assertEqual("invalid_pos_test_ratio", result.reason)

    def test_metrics_track_min_max_duration_and_first_crossing(self) -> None:
        result = evaluate_mechanism_records(
            [
                {"relative_time_s": 5.0, "pos_test_ratio": 0.25},
                {"relative_time_s": 7.5, "pos_test_ratio": 1.2},
                {"relative_time_s": 9.0, "pos_test_ratio": 0.7},
            ]
        )

        self.assertEqual(3, result.metrics["sample_count"])
        self.assertEqual(5.0, result.metrics["first_timestamp_s"])
        self.assertEqual(9.0, result.metrics["last_timestamp_s"])
        self.assertEqual(4.0, result.metrics["observation_duration_s"])
        self.assertEqual(0.25, result.metrics["min_pos_test_ratio"])
        self.assertEqual(1.2, result.metrics["max_pos_test_ratio"])
        self.assertEqual(7.5, result.metrics["first_crossing_time_s"])
        self.assertEqual(["relative_time_s"], result.source_fields["timestamp"])
        self.assertEqual(["pos_test_ratio"], result.source_fields["pos_test_ratio"])

    def test_sustained_rejection_uses_named_no_sitl_helper_default(self) -> None:
        result = evaluate_mechanism_records(_records(0.2, 1.1, 1.2, 0.8))

        self.assertTrue(result.metrics["sampled_rejection"])
        self.assertTrue(result.metrics["sustained_rejection"])
        self.assertEqual(2, result.metrics["sustained_rejection_min_samples"])
        self.assertEqual(2, result.metrics["max_consecutive_rejection_samples"])

    def test_optional_reject_glitch_and_failsafe_flags_are_preserved_as_metrics(self) -> None:
        result = evaluate_mechanism_records(
            [
                {
                    "time_s": 0.0,
                    "posTestRatio": 0.2,
                    "reject_flag": True,
                    "glitch_detected": 1,
                    "ekf_failsafe": 1.0,
                }
            ]
        )

        self.assertEqual("fused_below_gate", result.mechanism_state)
        self.assertTrue(result.metrics["sampled_rejection"])
        self.assertTrue(result.metrics["explicit_reject_flag_evidence"])
        self.assertTrue(result.metrics["glitch_flag_evidence"])
        self.assertTrue(result.metrics["failsafe_flag_evidence"])
        self.assertEqual(["reject_flag"], result.source_fields["reject"])
        self.assertEqual(["glitch_detected"], result.source_fields["glitch"])
        self.assertEqual(["ekf_failsafe"], result.source_fields["failsafe"])

    def test_out_of_order_timestamps_fail_closed(self) -> None:
        result = evaluate_mechanism_records(
            [
                {"time_s": 2.0, "posTestRatio": 0.5},
                {"time_s": 1.0, "posTestRatio": 1.5},
            ]
        )

        self.assertEqual("mechanism_unverified", result.mechanism_state)
        self.assertEqual("out_of_order_timestamps", result.reason)
        self.assertEqual(1, result.metrics["invalid_record_index"])

    def test_result_serializes_to_json_safe_dict(self) -> None:
        result = evaluate_mechanism_records(_records(0.5, 1.5))
        data = result.as_dict()

        self.assertEqual("rejected_above_gate", data["mechanism_state"])
        self.assertTrue(data["mechanism_evidence_accepted"])
        encoded = json.dumps(data, sort_keys=True)
        self.assertIn("first_crossing_time_s", encoded)
        self.assertNotIn("NaN", encoded)
        self.assertNotIn("Infinity", encoded)

    def test_mechanism_states_are_locked(self) -> None:
        self.assertEqual(
            (
                "fused_below_gate",
                "rejected_above_gate",
                "reset_detected",
                "mechanism_unverified",
            ),
            MECHANISM_STATES,
        )

    def test_analyzer_can_consume_mechanism_gate_result_shape(self) -> None:
        mechanism = evaluate_mechanism_records(_records(0.5, 1.5))
        observation = {
            "injection_triggered": True,
            "injection_readback_ok": True,
            "post_injection_s": 90.0,
            "required_artifacts_present": True,
            "mechanism_gate_result": mechanism,
            # Substantive behavior-tier fields, not a bare marker.
            "horizontal_gap_m": 40.0,
            "gap_growing": False,
            "attitude_in_band": True,
        }

        result = classify_observation(observation)

        self.assertTrue(result["accepted_observation"])
        self.assertEqual("detected_rejected", result["behavior_class"])
        self.assertEqual("valid_detected_rejection", result["reason"])

    def test_unverified_mechanism_gate_result_keeps_analysis_incomplete(self) -> None:
        mechanism = evaluate_mechanism_records([])
        observation = {
            "injection_triggered": True,
            "injection_readback_ok": True,
            "post_injection_s": 90.0,
            "required_artifacts_present": True,
            "mechanism_gate_result": mechanism.as_dict(),
            "horizontal_gap_m": 1.0,
            "gap_growing": False,
            "attitude_in_band": True,
        }

        result = classify_observation(observation)

        self.assertFalse(result["accepted_observation"])
        self.assertEqual("analysis_incomplete", result["behavior_class"])
        self.assertEqual("missing_mechanism_fields", result["reason"])

    def test_string_mechanism_marker_is_not_accepted(self) -> None:
        # A truthy non-bool mechanism-accepted marker must NOT become accepted.
        for marker in ("true", 1, "1", [1]):
            with self.subTest(marker=marker):
                observation = {
                    "injection_triggered": True,
                    "injection_readback_ok": True,
                    "post_injection_s": 90.0,
                    "required_artifacts_present": True,
                    "mechanism_gate_result": {
                        "accepted_evidence": marker,
                        "mechanism_state": "fused_below_gate",
                    },
                    "horizontal_gap_m": 0.5,
                    "gap_growing": False,
                    "attitude_in_band": True,
                }
                result = classify_observation(observation)
                self.assertFalse(result["accepted_observation"])
                self.assertEqual("analysis_incomplete", result["behavior_class"])
                self.assertEqual("missing_mechanism_fields", result["reason"])

    def test_malformed_post_injection_duration_fails_closed_without_raising(self) -> None:
        for bad in ("bad", None, [1.0], "90"):
            with self.subTest(bad=bad):
                observation = {
                    "injection_triggered": True,
                    "injection_readback_ok": True,
                    "post_injection_s": bad,
                    "required_artifacts_present": True,
                    "mechanism_evidence": True,
                    "horizontal_gap_m": 0.5,
                    "gap_growing": False,
                    "attitude_in_band": True,
                }
                result = classify_observation(observation)
                self.assertFalse(result["accepted_observation"])
                self.assertEqual("analysis_incomplete", result["behavior_class"])
                self.assertEqual(
                    "invalid_behavior_field_post_injection_s", result["reason"]
                )

    def test_no_sitl_gazebo_or_mavlink_command_is_invoked(self) -> None:
        with mock.patch.object(subprocess, "run", side_effect=AssertionError):
            result = evaluate_mechanism_records(_records(0.2, 1.2))

        self.assertEqual("rejected_above_gate", result.mechanism_state)

    def test_module_source_does_not_reference_runtime_launch_commands(self) -> None:
        source = (
            SRC
            / "sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/mechanism_gate.py"
        ).read_text(encoding="utf-8")

        forbidden = (
            "sim_vehicle.py",
            "gz sim",
            "gazebo",
            "mavlink_connection",
            "subprocess",
            "os.system",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
