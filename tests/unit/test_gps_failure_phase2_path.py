from __future__ import annotations

import sys
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sim_ard_gaw.campaigns.test_suite.core.models import (  # noqa: E402
    AttemptContext,
    AttemptRecord,
    AttemptStatus,
    Verdict,
    VerdictClass,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure import defaults  # noqa: E402
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.bin_analysis import (  # noqa: E402
    analyze_attempt_bin,
    decode_bin_records,
    extract_xkf4_mechanism,
    truth_vs_belief_from_decoded_records,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.case_generator import (  # noqa: E402
    GpsFailureCaseGenerator,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.config import (  # noqa: E402
    GpsFailureConfig,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.control import (  # noqa: E402
    GpsFailureMissionControl,
    MavlinkGpsMissionAdapter,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.environment import (  # noqa: E402
    GpsFailureEnvironment,
    build_launch_plan,
    identify_attempt_bin,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.mavlink import (  # noqa: E402
    connect_mavlink,
    read_live_contract_parameters,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.source_contract import (  # noqa: E402
    EKF_POS_HORIZ_ABS,
    EKF_PRED_POS_HORIZ_ABS,
    pos_test_ratio_from_live_pos_horiz_variance,
    pos_test_ratio_from_xkf4_sp,
    required_live_readback_names,
    validate_source_contract,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.telemetry import (  # noqa: E402
    request_telemetry_rates,
    normalize_message,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.monitor import (  # noqa: E402
    _LiveGpsMonitor,
    first_seq4_edge_after_armed_auto_front_half,
)
from sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure import (  # noqa: E402
    _accepted_live_record,
    _config_from_args,
    _parse_args,
)


class _FakeParamConnection:
    def __init__(self, values: dict[str, float] | None = None) -> None:
        self.values = dict(values or {})
        self.read_order: list[str] = []

    def read_parameter(self, name: str) -> float:
        self.read_order.append(name)
        if name not in self.values:
            raise TimeoutError(name)
        return self.values[name]

    def param_fetch_one(self, name: str) -> None:
        self.read_order.append(name)

    def param_set_send(self, name: str, value: float) -> None:
        self.values[name] = value

    def recv_match(self, **_kwargs: Any) -> Any:
        return None


class _FakeMav:
    def __init__(self) -> None:
        self.commands: list[tuple[Any, ...]] = []

    def command_long_send(self, *args: Any) -> None:
        self.commands.append(args)


class _FakeRateConnection:
    target_system = 7
    target_component = 1

    def __init__(self, *, ack: Any = "accepted") -> None:
        self.mav = _FakeMav()
        self.ack = ack

    def recv_match(self, **_kwargs: Any) -> Any:
        if self.ack == "accepted":
            return _Msg("COMMAND_ACK", command=511, result=0)
        if self.ack == "missing":
            return None
        return self.ack


class _Msg:
    def __init__(self, msg_type: str, **fields: Any) -> None:
        self._msg_type = msg_type
        for key, value in fields.items():
            setattr(self, key, value)

    def get_type(self) -> str:
        return self._msg_type


class _MissionAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def upload_mission(self, *args: Any) -> None:
        self.calls.append(("upload_mission", args))

    def verify_mission(self, *args: Any) -> None:
        self.calls.append(("verify_mission", args))

    def arm(self, *args: Any) -> None:
        self.calls.append(("arm", args))

    def set_mode(self, *args: Any) -> None:
        self.calls.append(("set_mode", args))


class _FakeMonitorConnection(_FakeRateConnection):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, float] = {}
        self.set_order: list[tuple[str, float]] = []
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def set_parameter(self, name: str, value: float) -> float:
        self.values[name] = value
        self.set_order.append((name, value))
        return value

    def read_parameter(self, name: str) -> float:
        return self.values[name]

    def param_fetch_one(self, name: str) -> None:
        return None

    def param_set_send(self, name: str, value: float) -> None:
        self.values[name] = value


class _StubbornProc:
    def __init__(self) -> None:
        self.terminated = False
        self.killed = False
        self.wait_calls = 0

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, *, timeout: float) -> None:
        self.wait_calls += 1
        if self.wait_calls == 1:
            raise subprocess.TimeoutExpired("fake", timeout)


def _valid_contract_readback_results() -> dict[str, dict[str, Any]]:
    values = {
        "EK3_POS_I_GATE": 500,
        "EK3_GLITCH_RAD": 25,
        "FS_EKF_THRESH": 0.8,
        "EK3_GPS_CHECK": 31,
        "EK3_SRC1_POSXY": 3,
        "EK3_SRC1_VELXY": 3,
        "EK3_SRC1_POSZ": 1,
        "EK3_SRC1_VELZ": 3,
        "EK3_SRC1_YAW": 1,
    }
    return {
        name: {"param": name, "value": value, "ok": True, "error": None}
        for name, value in values.items()
    }


def _valid_trigger_trace(*, include_latitude: bool = True) -> list[dict[str, Any]]:
    events = [
        {
            "seq": seq,
            "armed": True,
            "mode": "AUTO",
            "heartbeat_age_s": 0.1,
            "heartbeat_fresh": True,
            "simstate_age_s": 0.1,
            "simstate_fresh": True,
        }
        for seq in (1, 2, 3, 4)
    ]
    events[-1]["elapsed_since_trigger_s"] = 0.0
    if include_latitude:
        events[-1]["trigger_latitude_deg"] = 0.0
    return events


def _ctx(tmp: Path):
    case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("nominal")
    return AttemptContext(
        case=case,
        campaign_root=tmp,
        attempt_dir=tmp / "attempt",
        attempt_index=1,
        target_run_index=1,
        start_wall_s=0.0,
        start_monotonic_s=0.0,
    )


class GpsFailurePhase2SourceContractTests(unittest.TestCase):
    def test_required_live_readbacks_include_injected_knee_and_source_params(self) -> None:
        names = required_live_readback_names({"SIM_GPS1_JAM": 1.0})

        self.assertIn("SIM_GPS1_JAM", names)
        self.assertIn("EK3_POS_I_GATE", names)
        self.assertIn("EK3_GLITCH_RAD", names)
        self.assertIn("FS_EKF_THRESH", names)
        self.assertIn("EK3_GPS_CHECK", names)
        self.assertIn("EK3_SRC1_POSXY", names)
        self.assertIn("EK3_SRC1_VELXY", names)

    def test_source_contract_accepts_only_named_validated_proxy(self) -> None:
        readbacks = {
            "EK3_POS_I_GATE": 500,
            "EK3_GLITCH_RAD": 25,
            "FS_EKF_THRESH": 0.8,
            "EK3_GPS_CHECK": 31,
            "EK3_SRC1_POSXY": 3,
            "EK3_SRC1_VELXY": 3,
            "EK3_SRC1_POSZ": 1,
            "EK3_SRC1_VELZ": 3,
            "EK3_SRC1_YAW": 1,
        }
        contract = validate_source_contract(
            readbacks,
            estimator_flags=EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS,
        )

        self.assertTrue(contract.ok, contract.as_dict())
        self.assertTrue(contract.validated_proxy)
        self.assertFalse(contract.exact_aiding_proof)

    def test_source_contract_fails_closed_without_abs_flags_or_glitch_radius(self) -> None:
        readbacks = {
            "EK3_POS_I_GATE": 500,
            "EK3_GLITCH_RAD": 0,
            "FS_EKF_THRESH": 0.8,
            "EK3_GPS_CHECK": 31,
            "EK3_SRC1_POSXY": 3,
            "EK3_SRC1_VELXY": 3,
            "EK3_SRC1_POSZ": 1,
            "EK3_SRC1_VELZ": 3,
            "EK3_SRC1_YAW": 1,
        }
        contract = validate_source_contract(readbacks, estimator_flags=0)

        self.assertFalse(contract.ok)
        self.assertIn("ek3_glitch_rad_not_positive", contract.reasons)
        self.assertIn("ekf_pos_horiz_abs_flag_missing", contract.reasons)

    def test_source_contract_rejects_fractional_source_enum(self) -> None:
        readbacks = {
            "EK3_POS_I_GATE": 500,
            "EK3_GLITCH_RAD": 25,
            "FS_EKF_THRESH": 0.8,
            "EK3_GPS_CHECK": 31,
            "EK3_SRC1_POSXY": 3.5,
            "EK3_SRC1_VELXY": 3,
            "EK3_SRC1_POSZ": 1,
            "EK3_SRC1_VELZ": 3,
            "EK3_SRC1_YAW": 1,
        }
        contract = validate_source_contract(
            readbacks,
            estimator_flags=EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS,
        )

        self.assertFalse(contract.ok)
        self.assertIn("ek3_src1_posxy_not_integer", contract.reasons)

    def test_source_contract_validates_every_pinned_source_enum(self) -> None:
        base = {
            name: result["value"]
            for name, result in _valid_contract_readback_results().items()
        }
        expected = {
            "EK3_SRC1_POSXY": 3,
            "EK3_SRC1_VELXY": 3,
            "EK3_SRC1_POSZ": 1,
            "EK3_SRC1_VELZ": 3,
            "EK3_SRC1_YAW": 1,
        }
        for name, expected_value in expected.items():
            with self.subTest(name=name, kind="wrong"):
                readbacks = dict(base)
                readbacks[name] = expected_value + 1
                contract = validate_source_contract(
                    readbacks,
                    estimator_flags=EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS,
                )
                self.assertFalse(contract.ok)
                self.assertIn(f"{name.lower()}_unexpected_source", contract.reasons)
            with self.subTest(name=name, kind="fractional"):
                readbacks = dict(base)
                readbacks[name] = expected_value + 0.5
                contract = validate_source_contract(
                    readbacks,
                    estimator_flags=EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS,
                )
                self.assertFalse(contract.ok)
                self.assertIn(f"{name.lower()}_not_integer", contract.reasons)

    def test_source_contract_rejects_pinned_knee_parameter_mismatch(self) -> None:
        readbacks = {
            name: result["value"]
            for name, result in _valid_contract_readback_results().items()
        }
        readbacks["EK3_POS_I_GATE"] = 501

        contract = validate_source_contract(
            readbacks,
            estimator_flags=EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS,
        )

        self.assertFalse(contract.ok)
        self.assertIn("readback_mismatch:EK3_POS_I_GATE", contract.reasons)

    def test_ratio_helpers_reject_negative_square_root_fields(self) -> None:
        with self.assertRaises(ValueError):
            pos_test_ratio_from_live_pos_horiz_variance(-0.1)
        with self.assertRaises(ValueError):
            pos_test_ratio_from_xkf4_sp(-1)


class GpsFailurePhase2MavlinkTelemetryTests(unittest.TestCase):
    def test_connect_mavlink_uses_factory_only_when_supplied(self) -> None:
        calls: list[tuple[str, float]] = []

        def factory(endpoint: str, *, timeout_s: float):
            calls.append((endpoint, timeout_s))
            return _FakeParamConnection()

        conn = connect_mavlink("udpin:127.0.0.1:14551", timeout_s=1.5, factory=factory)

        self.assertIsInstance(conn, _FakeParamConnection)
        self.assertEqual([("udpin:127.0.0.1:14551", 1.5)], calls)

    def test_connect_mavlink_rejects_explicit_heartbeat_timeout(self) -> None:
        class _HeartbeatTimeoutConnection(_FakeParamConnection):
            def __init__(self) -> None:
                super().__init__()
                self.closed = False

            def wait_heartbeat(self, *, timeout: float) -> None:
                return None

            def close(self) -> None:
                self.closed = True

        connection = _HeartbeatTimeoutConnection()
        with self.assertRaisesRegex(TimeoutError, "no MAVLink heartbeat"):
            connect_mavlink(
                "udpin:127.0.0.1:14551",
                timeout_s=0.1,
                factory=lambda endpoint, *, timeout_s: connection,
            )
        self.assertTrue(connection.closed)

    def test_live_contract_readback_requests_every_required_name_once(self) -> None:
        values = {name: 1.0 for name in defaults.LIVE_READBACK_PARAMS}
        fake = _FakeParamConnection(values)
        result = read_live_contract_parameters(fake)

        self.assertEqual(sorted(defaults.LIVE_READBACK_PARAMS), fake.read_order)
        self.assertTrue(all(item.ok for item in result.values()))

    def test_request_telemetry_rates_uses_set_message_interval(self) -> None:
        fake = _FakeRateConnection()
        results = request_telemetry_rates(fake, rate_hz=2.0)

        self.assertTrue(all(item.ok for item in results))
        self.assertEqual(len(defaults.TELEMETRY_MESSAGE_TYPES), len(fake.mav.commands))
        self.assertEqual(500_000, fake.mav.commands[0][5])

    def test_request_telemetry_rates_fails_without_command_ack(self) -> None:
        fake = _FakeRateConnection(ack="missing")
        results = request_telemetry_rates(fake, rate_hz=2.0)

        self.assertFalse(any(item.ok for item in results))
        self.assertTrue(
            all(item.error == "missing_command_ack" for item in results),
            [item.as_dict() for item in results],
        )

    def test_normalize_ekf_status_derives_live_pos_test_ratio_and_preserves_clock(self) -> None:
        msg = _Msg(
            "EKF_STATUS_REPORT",
            pos_horiz_variance=1.5,
            flags=EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS,
        )
        sample = normalize_message(msg, arrival_monotonic_s=12.25)

        self.assertEqual("EKF_STATUS_REPORT", sample["type"])
        self.assertEqual(12.25, sample["arrival_monotonic_s"])
        self.assertEqual(2.25, sample["pos_test_ratio"])
        self.assertFalse(sample["gps_glitching"])

    def test_normalize_malformed_ekf_status_fails_closed_without_raising(self) -> None:
        sample = normalize_message(_Msg("EKF_STATUS_REPORT"), arrival_monotonic_s=2.0)

        self.assertEqual("EKF_STATUS_REPORT", sample["type"])
        self.assertFalse(sample["ok"])
        self.assertEqual(
            "missing_or_malformed_pos_horiz_variance",
            sample["error"],
        )

    def test_normalize_non_finite_attitude_never_reaches_json_artifacts(self) -> None:
        sample = normalize_message(
            _Msg("ATTITUDE", roll=float("nan"), pitch=float("inf"), yaw=0.0),
            arrival_monotonic_s=2.0,
        )

        self.assertIsNone(sample["roll_rad"])
        self.assertIsNone(sample["pitch_rad"])
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            defaults.write_json(Path(tmp) / "normalized.json", sample)

    def test_strict_atomic_json_rejects_nan_without_replacing_prior_file(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            path = Path(tmp) / "artifact.json"
            defaults.write_json(path, {"status": "original"})

            with self.assertRaises(ValueError):
                defaults.write_json(path, {"roll_rad": float("nan")})

            self.assertEqual({"status": "original"}, defaults.read_json(path))

    def test_normalize_heartbeat_maps_plane_auto_mode_for_trigger_evidence(self) -> None:
        sample = normalize_message(
            _Msg("HEARTBEAT", custom_mode=10, base_mode=128),
            arrival_monotonic_s=1.0,
        )

        self.assertEqual("AUTO", sample["mode"])
        self.assertTrue(sample["armed"])

    def test_trigger_helper_rejects_non_auto_trace(self) -> None:
        trace = [
            {"seq": 1, "armed": True, "mode": "MANUAL"},
            {"seq": 2, "armed": True, "mode": "MANUAL"},
            {"seq": 3, "armed": True, "mode": "MANUAL"},
            {"seq": 4, "armed": True, "mode": "MANUAL"},
        ]

        self.assertFalse(first_seq4_edge_after_armed_auto_front_half(trace))

    def test_trigger_helper_rejects_untimestamped_or_stale_state(self) -> None:
        untimestamped = [
            {"seq": seq, "armed": True, "mode": "AUTO"}
            for seq in (1, 2, 3, 4)
        ]
        stale = _valid_trigger_trace()
        stale[-1]["heartbeat_age_s"] = defaults.TRIGGER_HEARTBEAT_MAX_AGE_S + 0.01

        self.assertFalse(first_seq4_edge_after_armed_auto_front_half(untimestamped))
        self.assertFalse(first_seq4_edge_after_armed_auto_front_half(stale))


class GpsFailurePhase2BinAnalysisTests(unittest.TestCase):
    def test_xkf4_primary_core_comes_from_pi_and_sp_squares_to_ratio(self) -> None:
        result = extract_xkf4_mechanism(
            [
                {"type": "XKF4", "TimeUS": 100, "C": 0, "PI": 1, "SP": 20, "TS": 0},
                {
                    "type": "XKF4",
                    "TimeUS": 100,
                    "C": 1,
                    "PI": 1,
                    "SP": 150,
                    "TS": 1,
                    "OFN": 0,
                    "OFE": 0,
                },
                {
                    "type": "XKF4",
                    "TimeUS": 200,
                    "C": 1,
                    "PI": 1,
                    "SP": 80,
                    "TS": 0,
                    "OFN": 2,
                    "OFE": 3,
                },
            ]
        )

        self.assertTrue(result.ok, result.as_dict())
        self.assertEqual(1, result.primary_core)
        self.assertEqual(2.25, result.samples[0]["pos_test_ratio"])
        self.assertTrue(result.samples[0]["gps_position_rejected"])
        self.assertEqual(1, len(result.reset_events))

    def test_xkf4_fails_closed_on_primary_core_change(self) -> None:
        result = extract_xkf4_mechanism(
            [
                {"type": "XKF4", "TimeUS": 100, "C": 0, "PI": 0, "SP": 20},
                {"type": "XKF4", "TimeUS": 200, "C": 1, "PI": 1, "SP": 20},
            ]
        )

        self.assertFalse(result.ok)
        self.assertEqual("primary_core_changed", result.reason)

    def test_xkf4_fails_closed_when_any_primary_index_is_missing(self) -> None:
        result = extract_xkf4_mechanism(
            [
                {"type": "XKF4", "TimeUS": 100, "C": 0, "PI": 0, "SP": 20},
                {"type": "XKF4", "TimeUS": 100, "C": 1, "SP": 20},
            ]
        )

        self.assertFalse(result.ok)
        self.assertEqual("missing_xkf4_primary_index", result.reason)

    def test_xkf4_malformed_primary_record_fails_closed(self) -> None:
        result = extract_xkf4_mechanism(
            [
                {"type": "XKF4", "TimeUS": 100, "C": 0, "PI": 0, "SP": 20},
                {"type": "XKF4", "TimeUS": 200, "C": 0, "PI": 0},
            ]
        )

        self.assertFalse(result.ok)
        self.assertEqual("malformed_primary_core_xkf4", result.reason)

    def test_truth_vs_belief_pairs_sim_and_pos_only_within_skew(self) -> None:
        result = truth_vs_belief_from_decoded_records(
            [
                {"type": "SIM", "TimeUS": 1_000_000, "Lat": -353632620, "Lng": 1491652370},
                {"type": "POS", "TimeUS": 1_050_000, "Lat": -353632620, "Lng": 1491653370},
                {"type": "POS", "TimeUS": 1_300_000, "Lat": -353632620, "Lng": 1491653370},
            ]
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(1, len(result["samples"]))
        self.assertLess(result["samples"][0]["skew_s"], 0.1)
        self.assertGreater(result["samples"][0]["horizontal_gap_m"], 8.0)

    def test_truth_vs_belief_malformed_position_record_fails_closed(self) -> None:
        result = truth_vs_belief_from_decoded_records(
            [
                {"type": "SIM", "TimeUS": 1_000_000, "Lat": -353632620, "Lng": 1491652370},
                {"type": "POS", "TimeUS": 1_050_000, "Lat": -353632620},
            ]
        )

        self.assertFalse(result["ok"])
        self.assertEqual("malformed_position_records", result["reason"])

    def test_decode_bin_records_accepts_injected_decoder_without_pymavlink(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            bin_path = Path(tmp) / "attempt.BIN"
            bin_path.write_bytes(b"fake")

            records = decode_bin_records(
                bin_path,
                decoder=lambda path: [
                    {"type": "SIM", "TimeUS": 1, "Lat": 0, "Lng": 0, "path": path.name}
                ],
            )

        self.assertEqual("SIM", records[0]["type"])
        self.assertEqual("attempt.BIN", records[0]["path"])

    def test_analyze_attempt_bin_combines_xkf4_and_truth_belief(self) -> None:
        def decoder(_path: Path):
            return [
                {"type": "XKF4", "TimeUS": 80, "C": 0, "PI": 0, "SP": 500, "TS": 1},
                {"type": "CMD", "TimeUS": 90, "CNum": 4},
                {"type": "XKF4", "TimeUS": 100, "C": 0, "PI": 0, "SP": 120, "TS": 1},
                {"type": "XKF4", "TimeUS": 200, "C": 0, "PI": 0, "SP": 80, "TS": 0},
                {"type": "SIM", "TimeUS": 100, "Lat": 0, "Lng": 0},
                {"type": "POS", "TimeUS": 120, "Lat": 0, "Lng": 1000},
            ]

        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            result = analyze_attempt_bin(Path(tmp) / "attempt.BIN", decoder=decoder)

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["mechanism"]["ok"])
        self.assertTrue(result["truth_vs_belief"]["ok"])
        self.assertEqual(2, len(result["mechanism"]["samples"]))
        self.assertEqual(90, result["window_start_time_us"])

    def test_analyze_attempt_bin_fails_closed_without_injection_window_anchor(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            result = analyze_attempt_bin(
                Path(tmp) / "attempt.BIN",
                decoder=lambda _path: [
                    {"type": "XKF4", "TimeUS": 100, "C": 0, "PI": 0, "SP": 20},
                ],
            )

        self.assertFalse(result["ok"])
        self.assertEqual("injection_window_not_anchored", result["reason"])

    def test_truth_belief_growth_does_not_cross_reset_segments(self) -> None:
        result = truth_vs_belief_from_decoded_records(
            [
                {"type": "SIM", "TimeUS": 100, "Lat": 0, "Lng": 0},
                {"type": "POS", "TimeUS": 100, "Lat": 0, "Lng": 5000},
                {"type": "SIM", "TimeUS": 300, "Lat": 0, "Lng": 0},
                {"type": "POS", "TimeUS": 300, "Lat": 0, "Lng": 100},
            ],
            reset_event_times_us=[200],
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(1, result["active_segment_index"])
        self.assertEqual(1, len(result["samples"]))
        self.assertEqual(2, result["all_sample_count"])


class GpsFailurePhase2CliTests(unittest.TestCase):
    def test_live_cli_requires_explicit_confirmation(self) -> None:
        with self.assertRaises(SystemExit):
            _parse_args(["--live-case", "nominal"])

    def test_live_cli_sets_launch_stack_after_confirmation(self) -> None:
        args = _parse_args(["--live-case", "nominal", "--confirm-live-phase2"])
        config = _config_from_args(args)

        self.assertTrue(config.launch_stack)
        self.assertEqual(defaults.PHASE2_MONITOR_TIMEOUT_S, config.mission_timeout_s)

    def test_live_cli_rejects_unprotected_case(self) -> None:
        with self.assertRaises(SystemExit):
            _parse_args(["--live-case", "step_glitch_010m", "--confirm-live-phase2"])

    def test_live_record_gate_requires_terminal_success_and_acceptance(self) -> None:
        accepted = AttemptRecord(
            attempt_id="nominal__rep_01__attempt_001",
            suite_name="gps_failure",
            case_id="nominal",
            target_run_index=1,
            attempt_index=1,
            status=AttemptStatus.SUCCESS,
            verdict=Verdict(
                VerdictClass.SUCCESS,
                "nominal",
                False,
                metadata={"accepted_observation": True},
            ),
        )
        rejected = AttemptRecord(
            attempt_id="nominal__rep_01__attempt_002",
            suite_name="gps_failure",
            case_id="nominal",
            target_run_index=1,
            attempt_index=2,
            status=AttemptStatus.ANALYSIS_FAILED,
            verdict=Verdict(
                VerdictClass.ANALYSIS_FAILED,
                "analysis_incomplete",
                True,
                metadata={"accepted_observation": False},
            ),
        )

        self.assertTrue(_accepted_live_record(accepted))
        self.assertFalse(_accepted_live_record(rejected))


class GpsFailurePhase2MonitorTests(unittest.TestCase):
    def test_slow_drift_update_ramps_with_elapsed_time(self) -> None:
        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("slow_drift_0p5_mps")
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_monitor_drift")
        master = _FakeMonitorConnection()
        live = _LiveGpsMonitor(GpsFailureConfig(launch_stack=True), case, ctx, master)
        live.trigger_trace = _valid_trigger_trace()

        live._maybe_execute_slow_drift_update(5.0)

        self.assertTrue(live.ramp_update_results)
        payload = dict(master.set_order)
        self.assertGreater(payload["SIM_GPS1_GLTCH_Y"], 0.0)

    def test_slow_drift_missing_truth_latitude_fails_closed_without_write(self) -> None:
        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("slow_drift_0p5_mps")
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_monitor_no_lat")
        master = _FakeMonitorConnection()
        live = _LiveGpsMonitor(GpsFailureConfig(launch_stack=True), case, ctx, master)
        live.trigger_trace = _valid_trigger_trace(include_latitude=False)

        live._maybe_execute_slow_drift_update(5.0)

        self.assertEqual([], master.set_order)
        self.assertEqual("plan_not_ready", live.ramp_update_results[0]["result"]["reason"])
        self.assertEqual("slow_drift_update_failed", live.operation_failure_reason)

    def test_failed_initial_injection_is_latched_and_never_retried(self) -> None:
        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("slow_drift_0p5_mps")
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_monitor_one_shot")
        master = _FakeMonitorConnection()
        live = _LiveGpsMonitor(GpsFailureConfig(launch_stack=True), case, ctx, master)
        live.trigger_trace = _valid_trigger_trace(include_latitude=False)

        live._execute_initial_injection(time.monotonic())

        self.assertTrue(live.injection_attempted)
        self.assertFalse(live.triggered)
        self.assertEqual([], master.set_order)
        with self.assertRaisesRegex(RuntimeError, "one-shot"):
            live._execute_initial_injection(time.monotonic())

    def test_hard_denial_restore_executes_after_bounded_window(self) -> None:
        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("hard_denial_15s")
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_monitor_restore")
        master = _FakeMonitorConnection()
        live = _LiveGpsMonitor(GpsFailureConfig(launch_stack=True), case, ctx, master)
        live.trigger_trace = _valid_trigger_trace()

        live._execute_initial_injection(time.monotonic())
        live._maybe_execute_restore(15.0)

        self.assertIn(("SIM_GPS1_ENABLE", 0.0), master.set_order)
        self.assertIn(("SIM_GPS1_ENABLE", 1.0), master.set_order)
        self.assertTrue(live.restore_results)

    def test_failed_restore_gates_terminal_acceptance(self) -> None:
        class _RestoreMismatchConnection(_FakeMonitorConnection):
            def set_parameter(self, name: str, value: float) -> float:
                observed = super().set_parameter(name, value)
                if name == "SIM_GPS1_ENABLE" and value == 1.0:
                    return 0.0
                return observed

        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("hard_denial_15s")
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_monitor_restore_fail")
        master = _RestoreMismatchConnection()
        live = _LiveGpsMonitor(GpsFailureConfig(launch_stack=True), case, ctx, master)
        live.trigger_trace = _valid_trigger_trace()
        live._execute_initial_injection(100.0)

        live._maybe_execute_restore(15.0)
        status = live._scheduled_operation_status(90.0)

        self.assertEqual("restore_failed:0", live.operation_failure_reason)
        self.assertFalse(status["ok"])

    def test_trigger_recording_rejects_stale_heartbeat_and_simstate(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_stale_trigger")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        simstate = {"type": "SIMSTATE", "arrival_monotonic_s": 1.0, "lat_deg_e7": 0}
        live.normalized_messages.append(simstate)
        live._maybe_record_trigger_event(
            {"type": "HEARTBEAT", "arrival_monotonic_s": 1.0, "armed": True, "mode": "AUTO"}
        )
        for seq in (1, 2, 3, 4):
            live._maybe_record_trigger_event(
                {"type": "MISSION_CURRENT", "arrival_monotonic_s": 3.0 + seq, "seq": seq}
            )

        self.assertFalse(first_seq4_edge_after_armed_auto_front_half(live.trigger_trace))
        self.assertFalse(live.trigger_trace[0]["heartbeat_fresh"])
        self.assertFalse(live.trigger_trace[0]["simstate_fresh"])

    def test_attitude_envelope_ignores_pre_trigger_samples(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_post_slice")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        live.injection_monotonic_s = 100.0
        live.normalized_messages = [
            {"type": "ATTITUDE", "arrival_monotonic_s": 99.0, "roll_rad": 2.0, "pitch_rad": 0.0},
            {"type": "GLOBAL_POSITION_INT", "arrival_monotonic_s": 99.0, "relative_alt_mm": 200000},
            {"type": "ATTITUDE", "arrival_monotonic_s": 101.0, "roll_rad": 0.0, "pitch_rad": 0.0},
            {"type": "GLOBAL_POSITION_INT", "arrival_monotonic_s": 101.0, "relative_alt_mm": 100000},
        ]

        artifact = live._attitude_altitude_artifact()

        self.assertEqual([], artifact["threshold_crossings"])
        self.assertEqual(0.0, artifact["altitude_loss_m"])

    def test_real_post_trigger_mode_and_flight_excursions_are_not_hidden(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_excursion")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        defaults.write_json(ctx.attempt_dir / "gps_injection.json", {"case_id": ctx.case.case_id})
        ctx.extra["gps_live_contract_readbacks"] = _valid_contract_readback_results()
        live.triggered = True
        live.injection_monotonic_s = 100.0
        live.observation_end_monotonic_s = 191.0
        live.injection_result = {"success": True, "reason": "no_injection_writes"}
        live.trigger_trace = _valid_trigger_trace()
        live.normalized_messages = [
            {"type": "EKF_STATUS_REPORT", "arrival_monotonic_s": 101.0, "flags": EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS, "pos_horiz_variance": 0.5, "pos_test_ratio": 0.25},
            {"type": "SIMSTATE", "arrival_monotonic_s": 101.0, "lat_deg_e7": 0, "lon_deg_e7": 0},
            {"type": "GLOBAL_POSITION_INT", "arrival_monotonic_s": 101.01, "lat_deg_e7": 0, "lon_deg_e7": 0, "relative_alt_mm": 100000},
            {"type": "SIMSTATE", "arrival_monotonic_s": 190.0, "lat_deg_e7": 0, "lon_deg_e7": 0},
            {"type": "GLOBAL_POSITION_INT", "arrival_monotonic_s": 190.01, "lat_deg_e7": 0, "lon_deg_e7": 0, "relative_alt_mm": 60000},
            {"type": "ATTITUDE", "arrival_monotonic_s": 190.0, "roll_rad": 1.2, "pitch_rad": 0.0},
            {"type": "HEARTBEAT", "arrival_monotonic_s": 190.0, "armed": True, "mode": "RTL"},
        ]

        live._write_artifacts()
        observation = ctx.extra["gps_observation"]

        self.assertTrue(observation["mode_change"])
        self.assertTrue(observation["loss_of_control"])
        self.assertFalse(observation["attitude_in_band"])

    def test_write_artifacts_emits_required_observation_payloads(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_monitor_artifacts")
        case = ctx.case
        master = _FakeMonitorConnection()
        live = _LiveGpsMonitor(GpsFailureConfig(launch_stack=True), case, ctx, master)
        defaults.write_json(ctx.attempt_dir / "gps_injection.json", {"case_id": case.case_id})
        live.triggered = True
        live.injection_monotonic_s = time.monotonic() - defaults.MIN_POST_INJECTION_S - 1.0
        sample_time = live.injection_monotonic_s + 1.0
        live.injection_result = {"success": True, "reason": "no_injection_writes"}
        live.normalized_messages = [
            {"type": "EKF_STATUS_REPORT", "arrival_monotonic_s": sample_time, "pos_horiz_variance": 0.5, "pos_test_ratio": 0.25},
            {"type": "SIMSTATE", "arrival_monotonic_s": sample_time, "lat_deg_e7": 0, "lon_deg_e7": 0},
            {
                "type": "GLOBAL_POSITION_INT",
                "arrival_monotonic_s": sample_time + 0.02,
                "lat_deg_e7": 0,
                "lon_deg_e7": 0,
                "relative_alt_mm": 100000,
            },
            {"type": "ATTITUDE", "arrival_monotonic_s": sample_time, "roll_rad": 0.0, "pitch_rad": 0.0, "yaw_rad": 0.0},
            {"type": "HEARTBEAT", "arrival_monotonic_s": sample_time, "armed": True, "mode": "AUTO"},
        ]

        live._write_artifacts()

        for name in defaults.REQUIRED_ATTEMPT_ARTIFACTS:
            self.assertTrue((ctx.attempt_dir / name).exists(), name)
        self.assertTrue(ctx.extra["gps_observation"]["required_artifacts_present"])

    def test_mechanism_evidence_fails_closed_without_source_contract(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_monitor_source_fail")
        case = ctx.case
        master = _FakeMonitorConnection()
        live = _LiveGpsMonitor(GpsFailureConfig(launch_stack=True), case, ctx, master)
        defaults.write_json(ctx.attempt_dir / "gps_injection.json", {"case_id": case.case_id})
        live.triggered = True
        live.injection_monotonic_s = time.monotonic() - defaults.MIN_POST_INJECTION_S - 1.0
        sample_time = live.injection_monotonic_s + 1.0
        live.injection_result = {"success": True, "reason": "no_injection_writes"}
        live.normalized_messages = [
            {
                "type": "EKF_STATUS_REPORT",
                "arrival_monotonic_s": sample_time,
                "flags": EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS,
                "pos_horiz_variance": 0.5,
                "pos_test_ratio": 0.25,
            },
            {"type": "SIMSTATE", "arrival_monotonic_s": sample_time, "lat_deg_e7": 0, "lon_deg_e7": 0},
            {
                "type": "GLOBAL_POSITION_INT",
                "arrival_monotonic_s": sample_time + 0.02,
                "lat_deg_e7": 0,
                "lon_deg_e7": 0,
                "relative_alt_mm": 100000,
            },
            {"type": "ATTITUDE", "arrival_monotonic_s": sample_time, "roll_rad": 0.0, "pitch_rad": 0.0, "yaw_rad": 0.0},
        ]

        live._write_artifacts()

        observation = ctx.extra["gps_observation"]
        self.assertFalse(observation["mechanism_evidence"])
        self.assertFalse(observation["source_contract_ok"])
        self.assertTrue((ctx.attempt_dir / "source_contract.json").exists())

    def test_mechanism_evidence_requires_valid_source_contract(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_monitor_source_ok")
        case = ctx.case
        master = _FakeMonitorConnection()
        live = _LiveGpsMonitor(GpsFailureConfig(launch_stack=True), case, ctx, master)
        defaults.write_json(ctx.attempt_dir / "gps_injection.json", {"case_id": case.case_id})
        ctx.extra["gps_live_contract_readbacks"] = _valid_contract_readback_results()
        live.triggered = True
        live.injection_monotonic_s = time.monotonic() - defaults.MIN_POST_INJECTION_S - 1.0
        sample_time = live.injection_monotonic_s + 1.0
        live.injection_result = {"success": True, "reason": "no_injection_writes"}
        live.normalized_messages = [
            {
                "type": "EKF_STATUS_REPORT",
                "arrival_monotonic_s": sample_time,
                "flags": EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS,
                "pos_horiz_variance": 0.5,
                "pos_test_ratio": 0.25,
            },
            {"type": "SIMSTATE", "arrival_monotonic_s": sample_time, "lat_deg_e7": 0, "lon_deg_e7": 0},
            {
                "type": "GLOBAL_POSITION_INT",
                "arrival_monotonic_s": sample_time + 0.02,
                "lat_deg_e7": 0,
                "lon_deg_e7": 0,
                "relative_alt_mm": 100000,
            },
            {"type": "ATTITUDE", "arrival_monotonic_s": sample_time, "roll_rad": 0.0, "pitch_rad": 0.0, "yaw_rad": 0.0},
            {"type": "HEARTBEAT", "arrival_monotonic_s": sample_time, "armed": True, "mode": "AUTO"},
        ]

        live._write_artifacts()

        observation = ctx.extra["gps_observation"]
        self.assertTrue(observation["mechanism_evidence"])
        self.assertTrue(observation["source_contract_ok"])


class GpsFailurePhase2AdapterTests(unittest.TestCase):
    def test_launch_plan_uses_dedicated_gps_targets_and_var_attempt_runtime(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2")
        plan = build_launch_plan(ctx)

        self.assertIn("plane-gps", plan.sitl_command)
        self.assertIn("gazebo-plane-gps", plan.gazebo_command)
        self.assertIn("var/tmp_test_gps_phase2/attempt/runtime", str(plan.runtime_root))
        self.assertIn("var/runs/sitl/plane-gps/logs", str(plan.expected_bin_dir))

    def test_environment_launch_uses_injected_launcher_without_opening_real_stack(self) -> None:
        calls: list[tuple[list[str], Path]] = []

        class _Proc:
            def poll(self) -> None:
                return None

            def terminate(self) -> None:
                calls.append((["terminate"], Path(".")))

            def wait(self, *, timeout: float) -> None:
                return None

        def launcher(command: list[str], *, log_path: Path):
            calls.append((command, log_path))
            if "plane-gps" in command:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text("Cleanup complete\n", encoding="utf-8")
            return _Proc()

        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_env")
        env = GpsFailureEnvironment(GpsFailureConfig(launch_stack=True), launcher=launcher)

        env.launch(ctx.case, ctx)
        env.cleanup(ctx.case, ctx)

        self.assertIn("plane-gps", calls[0][0])
        self.assertIn("gazebo-plane-gps", calls[1][0])
        self.assertIn("gps_launch_plan", ctx.extra)
        self.assertEqual(set(), ctx.extra["gps_before_bin_names"])
        self.assertEqual({}, ctx.process_handles)

    def test_environment_ready_installs_production_mission_adapter(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_ready")
        master = _FakeMonitorConnection()
        def factory(endpoint: str, *, timeout_s: float):
            return master

        env = GpsFailureEnvironment(
            GpsFailureConfig(launch_stack=True),
            mavlink_factory=factory,
        )

        env.assert_ready(ctx.case, ctx)

        self.assertIs(ctx.extra["mavlink_master"], master)
        self.assertIsInstance(ctx.extra["mission_adapter"], MavlinkGpsMissionAdapter)

    def test_environment_cleanup_waits_kills_and_clears_handles(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_cleanup")
        proc = _StubbornProc()
        ctx.process_handles["plane-gps"] = proc
        env = GpsFailureEnvironment(
            GpsFailureConfig(launch_stack=True, cleanup_timeout_s=0.01)
        )

        env.cleanup(ctx.case, ctx)

        self.assertTrue(proc.terminated)
        self.assertTrue(proc.killed)
        self.assertEqual(2, proc.wait_calls)
        self.assertEqual({}, ctx.process_handles)

    def test_environment_cleanup_closes_mavlink_and_records_success(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_cleanup_mavlink")
        master = _FakeMonitorConnection()
        ctx.extra["mavlink_master"] = master
        env = GpsFailureEnvironment(GpsFailureConfig(launch_stack=True))

        env.cleanup(ctx.case, ctx)

        self.assertTrue(master.closed)
        self.assertTrue(ctx.extra["gps_cleanup"]["ok"])
        self.assertTrue(ctx.extra["gps_cleanup"]["mavlink_closed"])
        self.assertTrue((ctx.attempt_dir / "gps_cleanup.json").exists())
        self.assertIn("gps_cleanup.json", ctx.artifacts)

    def test_environment_cleanup_raises_when_process_survives_kill(self) -> None:
        class _NeverDiesProc:
            def terminate(self) -> None:
                return None

            def kill(self) -> None:
                return None

            def wait(self, *, timeout: float) -> None:
                raise subprocess.TimeoutExpired("fake", timeout)

        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_cleanup_failure")
        ctx.process_handles["plane-gps"] = _NeverDiesProc()
        env = GpsFailureEnvironment(
            GpsFailureConfig(launch_stack=True, cleanup_timeout_s=0.01)
        )

        with self.assertRaisesRegex(RuntimeError, "GPS cleanup failed"):
            env.cleanup(ctx.case, ctx)

        self.assertFalse(ctx.extra["gps_cleanup"]["ok"])
        self.assertEqual({}, ctx.process_handles)

    def test_attempt_bin_selection_uses_only_one_new_bin_without_stale_fallback(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_bin")
        plan = build_launch_plan(ctx)
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            bin_dir = Path(tmp) / "logs"
            bin_dir.mkdir(parents=True, exist_ok=True)
            stale = bin_dir / "00000001.BIN"
            fresh = bin_dir / "00000002.BIN"
            stale.write_bytes(b"stale")
            plan_dict = plan.as_dict()
            plan_dict["expected_bin_dir"] = str(bin_dir)
            ctx.extra["gps_launch_plan"] = plan_dict
            ctx.extra["gps_before_bin_names"] = {stale.name}

            self.assertIsNone(identify_attempt_bin(ctx))
            fresh.write_bytes(b"fresh")
            self.assertEqual(fresh, identify_attempt_bin(ctx))

            (bin_dir / "00000003.BIN").write_bytes(b"ambiguous")
            self.assertIsNone(identify_attempt_bin(ctx))

    def test_mission_control_uses_adapter_and_auto_mode(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_control")
        adapter = _MissionAdapter()
        ctx.extra["mission_adapter"] = adapter

        GpsFailureMissionControl(GpsFailureConfig(launch_stack=True)).execute(ctx.case, ctx)

        self.assertEqual(
            ["upload_mission", "verify_mission", "arm", "set_mode"],
            [name for name, _args in adapter.calls],
        )
        self.assertEqual(("AUTO",), adapter.calls[-1][1])


if __name__ == "__main__":
    unittest.main()
