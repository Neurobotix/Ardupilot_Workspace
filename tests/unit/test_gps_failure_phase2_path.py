from __future__ import annotations

import atexit
import shutil
import sys
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from pymavlink import mavutil as pymavlink_mavutil  # type: ignore[reportMissingImports]


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
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure import (  # noqa: E402
    mavlink as gps_mavlink,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.bin_analysis import (  # noqa: E402
    analyze_attempt_bin,
    decode_bin_records,
    extract_xkf4_mechanism,
    truth_vs_belief_from_decoded_records,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.analyzers import (  # noqa: E402
    GpsFailureAnalyzer,
    _trigger_window_time_us,
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
    _run_governed_cleanup,
    build_launch_plan,
    identify_attempt_bin,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.mavlink import (  # noqa: E402
    connect_mavlink,
    read_live_contract_parameters,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.manifest import (  # noqa: E402
    GpsFailureManifest,
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
    DELIVERY_REQUIRED_MESSAGE_TYPES,
    normalize_message,
    request_live_streams,
)
from sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.monitor import (  # noqa: E402
    _LiveGpsMonitor,
    first_seq4_edge_after_armed_auto_front_half,
)
from sim_ard_gaw.campaigns.test_suite.cli.run_gps_failure import (  # noqa: E402
    _accepted_live_record,
    _config_from_args,
    _parse_args,
    _workflow_complete_live_record,
    _write_campaign_contract,
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
        self.stream_requests: list[tuple[Any, ...]] = []

    def command_long_send(self, *args: Any) -> None:
        self.commands.append(args)

    def request_data_stream_send(self, *args: Any) -> None:
        self.stream_requests.append(args)


class _FakeRateConnection:
    target_system = 7
    target_component = 1

    def __init__(self, *, ack: Any = "accepted") -> None:
        self.mav = _FakeMav()
        self.ack = ack
        self.recv_calls = 0

    def recv_match(self, **_kwargs: Any) -> Any:
        self.recv_calls += 1
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
        for seq in (1, 3, 4)
    ]
    events[-1]["elapsed_since_trigger_s"] = 0.0
    if include_latitude:
        events[-1]["trigger_latitude_deg"] = 0.0
    return events


_CTX_SCRATCH_PATHS: set[Path] = set()


def _ctx(tmp: Path):
    # Ensure test scratch dirs under var/ are removed at process exit even when a
    # caller passes a fixed path (rather than a TemporaryDirectory). Without this
    # the hardcoded ROOT/var/tmp_test_gps_phase2_* trees leak into the working
    # tree on every run. Registration is idempotent per path.
    if tmp not in _CTX_SCRATCH_PATHS:
        _CTX_SCRATCH_PATHS.add(tmp)
        atexit.register(shutil.rmtree, tmp, ignore_errors=True)
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
            estimator_flags=EKF_POS_HORIZ_ABS,
        )

        self.assertTrue(contract.ok, contract.as_dict())
        self.assertTrue(contract.validated_proxy)
        self.assertFalse(contract.exact_aiding_proof)

    def test_source_contract_accepts_live_nominal_flags_without_predicted_abs(self) -> None:
        readbacks = {
            name: result["value"]
            for name, result in _valid_contract_readback_results().items()
        }

        contract = validate_source_contract(readbacks, estimator_flags=831)

        self.assertTrue(contract.ok, contract.as_dict())

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
        self.assertAlmostEqual(0.16, pos_test_ratio_from_xkf4_sp(0.4))
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

    def test_request_live_streams_uses_gps_owned_data_stream_requests(self) -> None:
        fake = _FakeRateConnection()
        result = request_live_streams(fake, rate_hz=2)

        self.assertEqual("MAV_DATA_STREAM", result["method"])
        self.assertEqual(
            "gps_failure.mavlink.request_live_streams",
            result["implementation"],
        )
        self.assertFalse(result["command_ack_required"])
        self.assertEqual(4, len(fake.mav.stream_requests))
        self.assertEqual(2, fake.mav.stream_requests[0][3])
        self.assertEqual([], fake.mav.commands)
        self.assertEqual(0, fake.recv_calls)

    def test_event_driven_statustext_ack_cannot_abort_stream_setup(self) -> None:
        class _NoAckConnection(_FakeRateConnection):
            def recv_match(self, **_kwargs: Any) -> Any:
                raise AssertionError("stream setup must not wait for COMMAND_ACK")

        result = request_live_streams(_NoAckConnection(), rate_hz=2)

        self.assertEqual(
            ["STATUSTEXT"], result["event_driven_optional_message_types"]
        )
        self.assertFalse(result["command_ack_required"])

    def test_request_live_streams_rejects_non_integer_or_nonpositive_rate(self) -> None:
        for rate in (0, -1, 2.5, True):
            with self.subTest(rate=rate), self.assertRaisesRegex(
                ValueError, "positive integer"
            ):
                request_live_streams(
                    _FakeRateConnection(),
                    rate_hz=rate,  # type: ignore[arg-type]
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

    def test_normalize_heartbeat_maps_plane_rtl_mode_for_terminal_detection(self) -> None:
        sample = normalize_message(
            _Msg("HEARTBEAT", custom_mode=11, base_mode=128),
            arrival_monotonic_s=1.0,
        )

        self.assertEqual("RTL", sample["mode"])
        self.assertTrue(sample["armed"])

    def test_trigger_helper_rejects_non_auto_trace(self) -> None:
        trace = [
            {"seq": 1, "armed": True, "mode": "MANUAL"},
            {"seq": 3, "armed": True, "mode": "MANUAL"},
            {"seq": 4, "armed": True, "mode": "MANUAL"},
        ]

        self.assertFalse(first_seq4_edge_after_armed_auto_front_half(trace))

    def test_trigger_helper_rejects_untimestamped_or_stale_state(self) -> None:
        untimestamped = [
            {"seq": seq, "armed": True, "mode": "AUTO"}
            for seq in (1, 3, 4)
        ]
        stale = _valid_trigger_trace()
        stale[-1]["heartbeat_age_s"] = defaults.TRIGGER_HEARTBEAT_MAX_AGE_S + 0.01

        self.assertFalse(first_seq4_edge_after_armed_auto_front_half(untimestamped))
        self.assertFalse(first_seq4_edge_after_armed_auto_front_half(stale))

    def test_trigger_helper_ignores_stale_progress_until_clean_sample_arrives(self) -> None:
        clean_seq1, clean_seq3, clean_seq4 = _valid_trigger_trace()
        stale_seq3 = {**clean_seq3, "heartbeat_age_s": 1.5, "heartbeat_fresh": False}

        self.assertTrue(
            first_seq4_edge_after_armed_auto_front_half(
                [clean_seq1, stale_seq3, clean_seq3, clean_seq4]
            )
        )

    def test_trigger_helper_does_not_authorize_without_clean_seq4_sample(self) -> None:
        clean_seq1, clean_seq3, clean_seq4 = _valid_trigger_trace()
        stale_seq4 = {**clean_seq4, "heartbeat_age_s": 1.5, "heartbeat_fresh": False}

        self.assertFalse(
            first_seq4_edge_after_armed_auto_front_half(
                [clean_seq1, clean_seq3, stale_seq4]
            )
        )

    def test_monitor_logs_stale_and_clean_trigger_evidence_for_operator(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_operator_trigger_logs")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        clean_seq1, clean_seq3, clean_seq4 = _valid_trigger_trace()
        stale_seq3 = {**clean_seq3, "heartbeat_age_s": 1.5, "heartbeat_fresh": False}

        with patch.object(defaults, "log") as log:
            live._log_trigger_evidence_event(clean_seq1)
            live._log_trigger_evidence_event(stale_seq3)
            live._log_trigger_evidence_event(clean_seq3)
            live._log_trigger_evidence_event(clean_seq4)

        messages = [str(call.args[0]) for call in log.call_args_list]
        self.assertTrue(any("clean trigger progress seq=1" in msg for msg in messages))
        self.assertTrue(
            any("ignoring stale/incomplete trigger evidence seq=3" in msg for msg in messages)
        )
        self.assertTrue(any("clean trigger progress seq=3" in msg for msg in messages))
        self.assertTrue(any("clean seq-4 trigger edge observed" in msg for msg in messages))

    def test_monitor_periodic_status_reports_waiting_and_post_trigger_state(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_operator_periodic_logs")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )

        with patch.object(defaults, "log") as log:
            live._log_periodic_operator_status(live.started_monotonic + 16.0)
            live.triggered = True
            live.injection_monotonic_s = live.started_monotonic + 20.0
            live.current_mode = "AUTO"
            live.max_seq_reached = 4
            live._log_periodic_operator_status(live.started_monotonic + 36.0)

        messages = [str(call.args[0]) for call in log.call_args_list]
        self.assertTrue(any("still waiting for clean seq-4 trigger" in msg for msg in messages))
        self.assertTrue(any("observing post-trigger" in msg for msg in messages))


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
                    "SP": 1.5,
                    "TS": 1,
                    "OFN": 0,
                    "OFE": 0,
                },
                {
                    "type": "XKF4",
                    "TimeUS": 200,
                    "C": 1,
                    "PI": 1,
                    "SP": 0.8,
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
                {"type": "SIM", "TimeUS": 1_000_000, "Lat": -35.3632620, "Lng": 149.1652370},
                {"type": "POS", "TimeUS": 1_050_000, "Lat": -35.3632620, "Lng": 149.1653370},
                {"type": "POS", "TimeUS": 1_300_000, "Lat": -35.3632620, "Lng": 149.1653370},
            ]
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(1, len(result["samples"]))
        self.assertLess(result["samples"][0]["skew_s"], 0.1)
        self.assertGreater(result["samples"][0]["horizontal_gap_m"], 8.0)

    def test_truth_vs_belief_malformed_position_record_fails_closed(self) -> None:
        result = truth_vs_belief_from_decoded_records(
            [
                {"type": "SIM", "TimeUS": 1_000_000, "Lat": -35.3632620, "Lng": 149.1652370},
                {"type": "POS", "TimeUS": 1_050_000, "Lat": -35.3632620},
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
                {"type": "XKF4", "TimeUS": 80, "C": 0, "PI": 0, "SP": 5.0, "TS": 1},
                {"type": "CMD", "TimeUS": 90, "CNum": 4},
                {"type": "XKF4", "TimeUS": 100, "C": 0, "PI": 0, "SP": 1.2, "TS": 1},
                {"type": "XKF4", "TimeUS": 200, "C": 0, "PI": 0, "SP": 0.8, "TS": 0},
                {"type": "SIM", "TimeUS": 100, "Lat": 0, "Lng": 0},
                {"type": "POS", "TimeUS": 120, "Lat": 0, "Lng": 0.001},
            ]

        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            result = analyze_attempt_bin(
                Path(tmp) / "attempt.BIN",
                decoder=decoder,
                window_start_time_us=95,
            )

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["mechanism"]["ok"])
        self.assertTrue(result["truth_vs_belief"]["ok"])
        self.assertEqual(2, len(result["mechanism"]["samples"]))
        self.assertEqual(95, result["window_start_time_us"])
        self.assertEqual("live_trigger_boot_time", result["window_anchor"])

    def test_analyze_attempt_bin_fails_closed_without_injection_window_anchor(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            result = analyze_attempt_bin(
                Path(tmp) / "attempt.BIN",
                decoder=lambda _path: [
                    {"type": "CMD", "TimeUS": 50, "CNum": 4},
                    {"type": "XKF4", "TimeUS": 100, "C": 0, "PI": 0, "SP": 20},
                ],
            )

        self.assertFalse(result["ok"])
        self.assertEqual("injection_window_not_anchored", result["reason"])

    def test_truth_belief_growth_does_not_cross_reset_segments(self) -> None:
        result = truth_vs_belief_from_decoded_records(
            [
                {"type": "SIM", "TimeUS": 100, "Lat": 0, "Lng": 0},
                {"type": "POS", "TimeUS": 100, "Lat": 0, "Lng": 0.0005},
                {"type": "SIM", "TimeUS": 300, "Lat": 0, "Lng": 0},
                {"type": "POS", "TimeUS": 300, "Lat": 0, "Lng": 0.00001},
            ],
            reset_event_times_us=[200],
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(1, result["active_segment_index"])
        self.assertEqual(1, len(result["samples"]))
        self.assertEqual(2, result["all_sample_count"])

    def test_analyzer_replaces_live_fallback_from_cleanup_finalized_bin(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            root = Path(tmp)
            ctx = _ctx(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            bin_path = bin_dir / "00000001.BIN"
            bin_path.write_bytes(b"finalized-bin")
            ctx.extra.update({
                "gps_launch_plan": {"expected_bin_dir": str(bin_dir)},
                "gps_before_bin_names": set(),
                "gps_trigger_trace": [{
                    "seq": 4,
                    "trigger_time_us": 95.0,
                    "trigger_boot_time_fresh": True,
                }],
                "gps_bin_decoder": lambda _path: [
                    {"type": "XKF4", "TimeUS": 100, "C": 0, "PI": 0, "SP": 0.5},
                    {"type": "XKF4", "TimeUS": 200, "C": 0, "PI": 0, "SP": 0.4},
                    {"type": "SIM", "TimeUS": 100, "Lat": 0.0, "Lng": 0.0},
                    {"type": "POS", "TimeUS": 100, "Lat": 0.0, "Lng": 0.000001},
                    {"type": "SIM", "TimeUS": 200, "Lat": 0.0, "Lng": 0.0},
                    {"type": "POS", "TimeUS": 200, "Lat": 0.0, "Lng": 0.000001},
                ],
                "gps_observation": {
                    "case_id": "nominal",
                    "fault_type": "nominal",
                    "injection_triggered": True,
                    "injection_readback_ok": True,
                    "post_injection_s": 21.0,
                    "required_post_injection_s": 20.0,
                    "required_artifacts_present": True,
                    "source_contract_ok": True,
                    "behavior_measurements_complete": True,
                    "horizontal_gap_m": 99.0,
                    "gap_growing": True,
                    "gap_within_nominal_band": False,
                    "attitude_in_band": True,
                    "fused": False,
                    "pos_test_ratio_rejected": True,
                    "reset_event": False,
                    "failsafe": False,
                    "mode_change": False,
                    "loss_of_control": False,
                    "terminal_state_reached": True,
                    "mission_complete": True,
                    "stop_reason": "planned_rtl_stabilized",
                    "max_seq_reached": 9,
                    "auto_to_rtl_transition_seq": 8,
                },
            })
            for name in defaults.REQUIRED_ATTEMPT_ARTIFACTS:
                payload: dict[str, Any] = {}
                if name == "ekf_innovation_metrics.json":
                    payload = {"pos_test_ratio": [99.0], "variance": []}
                elif name == "truth_vs_belief.json":
                    payload = {
                        "horizontal_gap_m": [99.0],
                        "truth_source": "SIMSTATE",
                        "belief_source": "GLOBAL_POSITION_INT",
                    }
                path = ctx.attempt_dir / name
                defaults.write_json(path, payload)
                ctx.artifacts[name] = path

            result = GpsFailureAnalyzer().analyze(ctx.case, ctx)

            self.assertTrue(result.ok, result.summary)
            self.assertEqual("nominal", result.summary["behavior_class"])
            metrics = defaults.read_json(
                ctx.attempt_dir / "ekf_innovation_metrics.json"
            )
            self.assertEqual(2, len(metrics["pos_test_ratio"]))
            self.assertAlmostEqual(0.25, metrics["pos_test_ratio"][0])
            self.assertAlmostEqual(0.16, metrics["pos_test_ratio"][1])
            self.assertEqual(
                len(b"finalized-bin"),
                metrics["bin_analysis"]["bin_provenance"]["size_bytes"],
            )
            expected_bin = (
                ctx.attempt_dir
                / f"{defaults.case_attempt_id('nominal', 1, 1)}.BIN"
            )
            self.assertTrue(expected_bin.exists())
            self.assertEqual(b"finalized-bin", expected_bin.read_bytes())
            self.assertEqual(expected_bin, ctx.artifacts["raw_log"])
            self.assertEqual(str(expected_bin), metrics["bin_analysis"]["bin_path"])
            self.assertEqual(
                str(expected_bin),
                metrics["bin_analysis"]["bin_provenance"]["path"],
            )
            self.assertEqual(
                str(expected_bin),
                ctx.extra["plugin_manifest_fields"]["raw_log_path"],
            )
            self.assertLess(ctx.extra["gps_observation"]["horizontal_gap_m"], 5.0)


class GpsFailurePhase2CliTests(unittest.TestCase):
    def test_live_cli_requires_explicit_confirmation(self) -> None:
        with self.assertRaises(SystemExit):
            _parse_args(["--live-case", "nominal"])

    def test_live_cli_sets_launch_stack_after_confirmation(self) -> None:
        args = _parse_args(["--live-case", "nominal", "--confirm-live-phase2"])
        config = _config_from_args(args)

        self.assertTrue(config.launch_stack)
        self.assertEqual(defaults.PHASE2_MONITOR_TIMEOUT_S, config.mission_timeout_s)
        self.assertTrue(config.force_arm)

    def test_live_cli_can_disable_force_arm(self) -> None:
        args = _parse_args(
            [
                "--live-case",
                "nominal",
                "--confirm-live-phase2",
                "--no-force-arm",
            ]
        )
        config = _config_from_args(args)

        self.assertTrue(config.launch_stack)
        self.assertFalse(config.force_arm)

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

    def test_campaign_cli_requires_separate_campaign_confirmation(self) -> None:
        with self.assertRaises(SystemExit):
            _parse_args([
                "--live-phase2-round-robin-campaign",
                "--confirm-live-phase2",
            ])

    def test_campaign_cli_accepts_protected_round_robin_contract(self) -> None:
        args = _parse_args([
            "--live-phase2-round-robin-campaign",
            "--confirm-live-phase2",
            "--confirm-live-campaign",
            "--campaign-cases",
            "nominal,slow_drift_0p5_mps,hard_denial_15s",
            "--runs-per-case",
            "5",
        ])

        self.assertEqual(
            ["nominal", "slow_drift_0p5_mps", "hard_denial_15s"],
            args.campaign_cases,
        )
        self.assertEqual(5, args.runs_per_case)

    def test_workflow_record_gate_does_not_require_analysis_acceptance(self) -> None:
        record = AttemptRecord(
            attempt_id="hard_denial_15s__rep_01__attempt_001",
            suite_name="gps_failure",
            case_id="hard_denial_15s",
            target_run_index=1,
            attempt_index=1,
            status=AttemptStatus.SUCCESS,
            verdict=Verdict(
                VerdictClass.ANALYSIS_FAILED,
                "analysis_incomplete",
                True,
                metadata={"accepted_observation": False},
            ),
            artifacts={"raw_log": "/tmp/attempt.BIN"},
            plugin_manifest_fields={
                "workflow_status": "complete",
                "cleanup": {"ok": True},
            },
        )

        self.assertTrue(_workflow_complete_live_record(record))
        self.assertFalse(_accepted_live_record(record))

    def test_campaign_contract_rejects_drift_on_existing_root(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            config = GpsFailureConfig(campaign_root=Path(tmp))
            _write_campaign_contract(
                config=config,
                case_ids=["nominal"],
                runs_per_case=5,
                inter_attempt_delay_s=0.0,
            )

            with self.assertRaises(SystemExit):
                _write_campaign_contract(
                    config=config,
                    case_ids=["nominal"],
                    runs_per_case=4,
                    inter_attempt_delay_s=0.0,
                )


class GpsFailurePhase2MonitorTests(unittest.TestCase):
    def test_source_contract_uses_pre_injection_flags_not_post_fault_flags(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_pre_source_contract")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        ctx.extra["gps_live_contract_readbacks"] = _valid_contract_readback_results()
        live.pre_injection_estimator_flags = EKF_POS_HORIZ_ABS
        live.triggered = True
        live.injection_monotonic_s = 10.0
        live.normalized_messages = [
            {
                "type": "EKF_STATUS_REPORT",
                "arrival_monotonic_s": 11.0,
                "flags": 0,
            }
        ]

        artifact = live._source_contract_artifact()

        self.assertTrue(artifact["ok"], artifact)
        self.assertEqual("pre_injection", artifact["proof_stage"])
        self.assertEqual(EKF_POS_HORIZ_ABS, artifact["pre_injection_estimator_flags"])
        self.assertEqual(0, artifact["post_injection_estimator_flags"])

    def test_minimum_observation_window_does_not_end_flight(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_min_window_not_terminal")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        live.triggered = True
        live.injection_monotonic_s = 100.0
        live.max_seq_reached = 4

        self.assertGreaterEqual(
            live._post_injection_s(121.0), live._required_post_injection_s()
        )
        self.assertFalse(live._should_stop(121.0))
        self.assertFalse(live.terminal_state_reached)
        self.assertEqual("trigger_not_observed", live.stop_reason)

    def test_planned_rtl_stops_only_after_stabilization(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_planned_rtl")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        live.triggered = True
        live.injection_monotonic_s = 100.0
        live._record_flight_progress(
            {"type": "MISSION_CURRENT", "seq": 8}, 150.0
        )
        live._record_flight_progress(
            {"type": "MISSION_ITEM_REACHED", "seq": 8}, 151.0
        )
        live._record_flight_progress(
            {"type": "HEARTBEAT", "mode": "AUTO", "armed": True}, 152.0
        )
        live._record_flight_progress(
            {"type": "HEARTBEAT", "mode": "RTL", "armed": True}, 153.0
        )

        self.assertFalse(live._should_stop(162.99))
        self.assertTrue(live._should_stop(163.0))
        self.assertTrue(live._mission_complete())
        self.assertEqual("planned_rtl_stabilized", live.stop_reason)
        self.assertEqual([8], live.reached)

    def test_reached_waypoints_are_unique_real_reached_events(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_reached_waypoints")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        for arrival, seq in ((1.0, 4), (1.1, 4), (1.2, 5)):
            live._record_flight_progress(
                {"type": "MISSION_ITEM_REACHED", "seq": seq}, arrival
            )

        self.assertEqual([4, 5], live.reached)
        self.assertEqual(5, live.max_seq_reached)

    def test_analysis_anchor_uses_immutable_first_trigger_event(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_first_trigger_anchor")
        ctx.extra.update(
            {
                "gps_trigger_event": {
                    "seq": 4,
                    "trigger_time_us": 83_186_000.0,
                    "trigger_boot_time_fresh": True,
                },
                "gps_trigger_trace": [
                    {
                        "seq": 4,
                        "trigger_time_us": 83_186_000.0,
                        "trigger_boot_time_fresh": True,
                    },
                    {
                        "seq": 4,
                        "trigger_time_us": 102_686_000.0,
                        "trigger_boot_time_fresh": True,
                    },
                ],
            }
        )

        self.assertEqual(83_186_000.0, _trigger_window_time_us(ctx))

    def test_monitor_ignores_home_prelude_before_trigger_progress(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_home_prelude")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        live.normalized_messages.append(
            {
                "type": "SIMSTATE",
                "arrival_monotonic_s": 1.0,
                "lat_deg_e7": 0,
            }
        )
        live._maybe_record_trigger_event(
            {
                "type": "HEARTBEAT",
                "arrival_monotonic_s": 1.0,
                "armed": True,
                "mode": "AUTO",
            }
        )
        for arrival, seq in ((1.1, 0), (1.2, 0), (1.3, 1), (1.4, 3), (1.5, 4)):
            live._maybe_record_trigger_event(
                {
                    "type": "MISSION_CURRENT",
                    "arrival_monotonic_s": arrival,
                    "seq": seq,
                }
            )

        self.assertEqual([1, 3, 4], [event["seq"] for event in live.trigger_trace])
        self.assertTrue(first_seq4_edge_after_armed_auto_front_half(live.trigger_trace))

    def test_trigger_records_fresh_boot_time_for_dataflash_window(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_trigger_boot_time")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        live.normalized_messages.extend([
            {
                "type": "SIMSTATE",
                "arrival_monotonic_s": 1.0,
                "lat_deg_e7": 0,
            },
            {
                "type": "ATTITUDE",
                "arrival_monotonic_s": 1.45,
                "time_boot_ms": 84_250,
            },
        ])
        live._maybe_record_trigger_event({
            "type": "HEARTBEAT",
            "arrival_monotonic_s": 1.0,
            "armed": True,
            "mode": "AUTO",
        })
        live._maybe_record_trigger_event({
            "type": "MISSION_CURRENT",
            "arrival_monotonic_s": 1.5,
            "seq": 4,
        })

        event = live.trigger_trace[-1]
        self.assertTrue(event["trigger_boot_time_fresh"])
        self.assertEqual(84_250, event["trigger_time_boot_ms"])
        self.assertEqual(84_250_000, event["trigger_time_us"])
        self.assertEqual("ATTITUDE", event["trigger_time_source"])

    def test_trigger_ignores_unready_seq1_prelude_before_progress(self) -> None:
        trace = [
            {
                "seq": 1,
                "armed": False,
                "mode": None,
                "heartbeat_age_s": None,
                "heartbeat_fresh": False,
                "simstate_age_s": None,
                "simstate_fresh": False,
            },
            {
                "seq": 1,
                "armed": True,
                "mode": "AUTO",
                "heartbeat_age_s": 0.1,
                "heartbeat_fresh": True,
                "simstate_age_s": 0.1,
                "simstate_fresh": True,
            },
            {
                "seq": 3,
                "armed": True,
                "mode": "AUTO",
                "heartbeat_age_s": 0.1,
                "heartbeat_fresh": True,
                "simstate_age_s": 0.1,
                "simstate_fresh": True,
            },
            {
                "seq": 4,
                "armed": True,
                "mode": "AUTO",
                "heartbeat_age_s": 0.1,
                "heartbeat_fresh": True,
                "simstate_age_s": 0.1,
                "simstate_fresh": True,
            },
        ]

        self.assertTrue(first_seq4_edge_after_armed_auto_front_half(trace))

    def test_trigger_ignores_stale_repeated_current_sequence(self) -> None:
        trace = [
            {
                "seq": 1,
                "armed": True,
                "mode": "AUTO",
                "heartbeat_age_s": 0.1,
                "heartbeat_fresh": True,
                "simstate_age_s": 0.1,
                "simstate_fresh": True,
            },
            {
                "seq": 1,
                "armed": True,
                "mode": "AUTO",
                "heartbeat_age_s": 1.2,
                "heartbeat_fresh": False,
                "simstate_age_s": 0.1,
                "simstate_fresh": True,
            },
            {
                "seq": 3,
                "armed": True,
                "mode": "AUTO",
                "heartbeat_age_s": 0.1,
                "heartbeat_fresh": True,
                "simstate_age_s": 0.1,
                "simstate_fresh": True,
            },
            {
                "seq": 4,
                "armed": True,
                "mode": "AUTO",
                "heartbeat_age_s": 0.1,
                "heartbeat_fresh": True,
                "simstate_age_s": 0.1,
                "simstate_fresh": True,
            },
        ]

        self.assertTrue(first_seq4_edge_after_armed_auto_front_half(trace))

    def test_monitor_retains_home_regression_after_progress(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_home_regression")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        live.normalized_messages.append(
            {
                "type": "SIMSTATE",
                "arrival_monotonic_s": 1.0,
                "lat_deg_e7": 0,
            }
        )
        live._maybe_record_trigger_event(
            {
                "type": "HEARTBEAT",
                "arrival_monotonic_s": 1.0,
                "armed": True,
                "mode": "AUTO",
            }
        )
        for arrival, seq in ((1.1, 1), (1.2, 0), (1.3, 3), (1.4, 4)):
            live._maybe_record_trigger_event(
                {
                    "type": "MISSION_CURRENT",
                    "arrival_monotonic_s": arrival,
                    "seq": seq,
                }
            )

        self.assertEqual([1, 0, 3, 4], [event["seq"] for event in live.trigger_trace])
        self.assertFalse(first_seq4_edge_after_armed_auto_front_half(live.trigger_trace))

    def test_monitor_does_not_abort_on_command_ack_absence(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_no_ack_abort")
        master = _FakeMonitorConnection()
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            master,
        )
        live.deadline = time.monotonic() - 1.0

        with patch.object(live, "_read_source_contract_parameters") as readbacks:
            live.run()

        readbacks.assert_called_once_with()
        self.assertEqual("monitor_timeout", live.stop_reason)
        self.assertEqual(4, len(master.mav.stream_requests))
        self.assertEqual([], master.mav.commands)
        self.assertFalse(
            ctx.extra["gps_telemetry_stream_request"]["command_ack_required"]
        )

    def test_slow_drift_update_ramps_with_elapsed_time(self) -> None:
        case = GpsFailureCaseGenerator(GpsFailureConfig()).get_case("slow_drift_0p5_mps")
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_monitor_drift")
        master = _FakeMonitorConnection()
        live = _LiveGpsMonitor(GpsFailureConfig(launch_stack=True), case, ctx, master)
        defaults.write_json(ctx.attempt_dir / "run_config.json", {"case_id": case.case_id})
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
        for seq in (1, 3, 4):
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

    def test_telemetry_delivery_is_gated_by_observed_messages(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_delivery_gate")
        live = _LiveGpsMonitor(
            GpsFailureConfig(launch_stack=True),
            ctx.case,
            ctx,
            _FakeMonitorConnection(),
        )
        live.normalized_messages = [
            {"type": message_type, "arrival_monotonic_s": 1.0}
            for message_type in DELIVERY_REQUIRED_MESSAGE_TYPES
            if message_type != "GPS_RAW_INT"
        ]

        incomplete = live._telemetry_delivery_status()
        self.assertFalse(incomplete["ok"])
        self.assertEqual(["GPS_RAW_INT"], incomplete["missing_message_types"])

        live.normalized_messages.append(
            {"type": "GPS_RAW_INT", "arrival_monotonic_s": 1.1}
        )
        complete = live._telemetry_delivery_status()
        self.assertTrue(complete["ok"])
        self.assertEqual([], complete["missing_message_types"])
        self.assertEqual(
            ["STATUSTEXT"], complete["event_driven_optional_message_types"]
        )

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
        defaults.write_json(
            ctx.attempt_dir / "run_config.json",
            {"case_id": case.case_id},
        )
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
        self.assertIn("gps_injection.json", ctx.artifacts)
        self.assertTrue(ctx.stimulus_result["live_execution"]["success"])

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
        live.pre_injection_estimator_flags = EKF_POS_HORIZ_ABS | EKF_PRED_POS_HORIZ_ABS
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
    def test_gps_plugin_does_not_depend_on_sibling_plugins(self) -> None:
        plugin_dir = (
            ROOT
            / "src"
            / "sim_ard_gaw"
            / "campaigns"
            / "test_suite"
            / "plugins"
            / "gps_failure"
        )
        offenders = [
            path.relative_to(ROOT).as_posix()
            for path in plugin_dir.glob("*.py")
            if "airspeed_failure" in path.read_text(encoding="utf-8")
        ]

        self.assertEqual([], offenders)

    def test_gps_vehicle_gate_rejects_initialising_until_two_ready_heartbeats(self) -> None:
        required_ekf_flags = (
            getattr(pymavlink_mavutil.mavlink, "EKF_ATTITUDE", 1)
            | getattr(
                pymavlink_mavutil.mavlink,
                "EKF_VELOCITY_HORIZ",
                2,
            )
            | getattr(
                pymavlink_mavutil.mavlink,
                "EKF_POS_HORIZ_ABS",
                8,
            )
        )

        class _StreamMav:
            def request_data_stream_send(self, *_args: Any) -> None:
                return None

        class _ReadinessMaster:
            target_system = 1
            target_component = 1

            def __init__(self) -> None:
                self.mav = _StreamMav()
                self.messages = [
                    _Msg("GPS_RAW_INT", fix_type=3, satellites_visible=8),
                    _Msg("EKF_STATUS_REPORT", flags=required_ekf_flags),
                    _Msg("HEARTBEAT", mode="INITIALISING"),
                    _Msg("HEARTBEAT", mode="AUTO"),
                    _Msg("HEARTBEAT", mode="AUTO"),
                ]
                self.recv_calls = 0

            def mode_mapping(self) -> dict[str, int]:
                return {"AUTO": 10}

            def recv_match(self, **_kwargs: Any) -> Any:
                self.recv_calls += 1
                if self.messages:
                    return self.messages.pop(0)
                return None

        master = _ReadinessMaster()
        with patch.object(
            pymavlink_mavutil,
            "mode_string_v10",
            side_effect=lambda message: message.mode,
        ):
            gps_mavlink.wait_for_vehicle_ready(
                master,  # type: ignore[arg-type]
                0.5,
                force_arm=True,
            )

        self.assertEqual(5, master.recv_calls)

    def test_gps_vehicle_gate_timeout_reports_each_readiness_signal(self) -> None:
        class _StreamMav:
            def request_data_stream_send(self, *_args: Any) -> None:
                return None

        class _SilentMaster:
            target_system = 1
            target_component = 1
            mav = _StreamMav()

            def mode_mapping(self) -> dict[str, int]:
                return {}

            def recv_match(self, **_kwargs: Any) -> Any:
                return None

        with self.assertRaises(TimeoutError) as raised:
            gps_mavlink.wait_for_vehicle_ready(
                _SilentMaster(),  # type: ignore[arg-type]
                0.0,
                force_arm=True,
            )

        message = str(raised.exception)
        self.assertIn("auto_available=False", message)
        self.assertIn("gps_ready=False", message)
        self.assertIn("ekf_ready=False", message)
        self.assertIn("message_counts=", message)

    def test_production_mission_adapter_uses_only_gps_owned_protocol(self) -> None:
        master = object()
        config = GpsFailureConfig(launch_stack=True)
        adapter = MavlinkGpsMissionAdapter(master, config)
        uploaded = [object()]

        with patch.object(
            gps_mavlink,
            "upload_mission",
            return_value=uploaded,
        ) as upload, patch.object(gps_mavlink, "verify_mission") as verify, patch.object(
            gps_mavlink,
            "arm_vehicle",
        ) as arm, patch.object(
            gps_mavlink,
            "settle_after_arm_before_auto",
        ) as settle, patch.object(gps_mavlink, "set_auto_mode") as auto:
            adapter.upload_mission(str(defaults.MISSION_FILE))
            adapter.verify_mission(str(defaults.MISSION_FILE))
            adapter.arm()
            adapter.set_mode("AUTO")

        upload.assert_called_once_with(
            master,
            defaults.MISSION_FILE,
            config.upload_timeout_s,
        )
        verify.assert_called_once_with(master, uploaded, config.upload_timeout_s)
        arm.assert_called_once_with(master, config.arm_timeout_s, config.force_arm)
        settle.assert_called_once_with(master, defaults.AUTO_ARM_TO_AUTO_SETTLE_S)
        auto.assert_called_once_with(master, config.mode_timeout_s)

    def test_governed_cleanup_uses_canonical_launcher_without_shell(self) -> None:
        events: list[str] = []
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Cleanup complete\n",
            stderr="",
        )

        def run_canonical(*_args: Any, **_kwargs: Any) -> Any:
            events.append("canonical")
            return completed

        with patch(
            "sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.environment._cleanup_workspace_owned_processes",
            side_effect=lambda: events.append("owned"),
        ) as owned_cleanup, patch(
            "sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.environment.subprocess.run",
            side_effect=run_canonical,
        ) as run:
            result = _run_governed_cleanup(timeout_s=4.0)

        owned_cleanup.assert_called_once_with()
        self.assertEqual(["owned", "canonical"], events)
        run.assert_called_once_with(
            [str(ROOT / "scripts" / "ops" / "launch.sh"), "cleanup"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=4.0,
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["owned_cleanup"]["ok"])
        self.assertEqual("Cleanup complete\n", result["stdout"])

    def test_canonical_cleanup_matches_python_named_mavproxy(self) -> None:
        launcher = ROOT / "src" / "sim_ard_gaw" / "launch" / "launch.sh"
        source = launcher.read_text(encoding="utf-8")

        self.assertIn('pkill -9 -f "[m]avproxy.py"', source)

    def test_governed_cleanup_fails_closed_when_owned_cleanup_raises(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Cleanup complete\n",
            stderr="",
        )
        with patch(
            "sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.environment._cleanup_workspace_owned_processes",
            side_effect=RuntimeError("owned cleanup failure"),
        ), patch(
            "sim_ard_gaw.campaigns.test_suite.plugins.gps_failure.environment.subprocess.run",
            return_value=completed,
        ):
            result = _run_governed_cleanup(timeout_s=4.0)

        self.assertFalse(result["ok"])
        self.assertFalse(result["owned_cleanup"]["ok"])
        self.assertIn("owned cleanup failure", result["error"])

    def test_gps_manifest_persists_framework_terminal_status(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "var") as tmp:
            root = Path(tmp)
            record = AttemptRecord(
                attempt_id="nominal__rep_01__attempt_001",
                suite_name="gps_failure",
                case_id="nominal",
                target_run_index=1,
                attempt_index=1,
                status=AttemptStatus.ERROR,
                verdict=Verdict(
                    klass=VerdictClass.FAILED_RETRYABLE,
                    reason="error",
                    retryable=True,
                ),
            )

            GpsFailureManifest(root).append_attempt(record)

            saved = GpsFailureManifest(root).load()["attempts"][0]
            self.assertEqual("error", saved["status"])
            self.assertIsNone(saved["monitor_result"])

    def test_launch_plan_uses_dedicated_gps_targets_and_var_attempt_runtime(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2")
        plan = build_launch_plan(ctx)

        self.assertIn("plane-gps", plan.sitl_command)
        self.assertIn("gazebo-plane-gps", plan.gazebo_command)
        self.assertIn("var/tmp_test_gps_phase2/attempt/runtime", str(plan.runtime_root))
        self.assertIn("var/runs/sitl/plane-gps/logs", str(plan.expected_bin_dir))

    def test_environment_launch_uses_injected_launcher_without_opening_real_stack(self) -> None:
        calls: list[tuple[list[str], Path]] = []
        cleanup_calls: list[float] = []

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
        def governed_cleanup(*, timeout_s: float) -> dict[str, Any]:
            cleanup_calls.append(timeout_s)
            return {"attempted": True, "ok": True}

        env = GpsFailureEnvironment(
            GpsFailureConfig(launch_stack=True),
            launcher=launcher,
            governed_cleanup=governed_cleanup,
            process_scanner=lambda: [],
        )
        expected_before = {
            path.name
            for path in (
                defaults.VAR_ROOT / "runs" / "sitl" / defaults.SITL_TARGET / "logs"
            ).glob("*.BIN")
        }

        env.launch(ctx.case, ctx)
        env.cleanup(ctx.case, ctx)

        self.assertIn("plane-gps", calls[0][0])
        self.assertIn("gazebo-plane-gps", calls[1][0])
        self.assertIn("gps_launch_plan", ctx.extra)
        self.assertIn("run_config.json", ctx.artifacts)
        run_config = defaults.read_json(ctx.artifacts["run_config.json"])
        self.assertEqual("nominal", run_config["case_id"])
        self.assertEqual(64, len(run_config["mission_file_provenance"]["sha256"]))
        self.assertEqual(
            str(defaults.GAZEBO_WORLD_FILE), run_config["gazebo_world"]
        )
        self.assertEqual(64, len(run_config["gazebo_world_provenance"]["sha256"]))
        self.assertEqual(2, len(run_config["param_file_provenance"]))
        self.assertIn("git_head", run_config["source_tree_snapshot"])
        self.assertEqual(expected_before, ctx.extra["gps_before_bin_names"])
        self.assertEqual({}, ctx.process_handles)
        self.assertEqual([defaults.CLEANUP_TIMEOUT_S], cleanup_calls)

    def test_environment_ready_installs_production_mission_adapter(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_ready")
        master = _FakeMonitorConnection()
        readiness_calls: list[tuple[Any, float, bool]] = []
        def factory(endpoint: str, *, timeout_s: float):
            return master

        def vehicle_readiness(
            master: Any,
            timeout_s: float,
            *,
            force_arm: bool,
        ) -> None:
            readiness_calls.append((master, timeout_s, force_arm))

        env = GpsFailureEnvironment(
            GpsFailureConfig(launch_stack=True),
            mavlink_factory=factory,
            vehicle_readiness=vehicle_readiness,
        )

        env.assert_ready(ctx.case, ctx)

        self.assertIs(ctx.extra["mavlink_master"], master)
        self.assertIsInstance(ctx.extra["mission_adapter"], MavlinkGpsMissionAdapter)
        self.assertEqual(
            [(master, defaults.VEHICLE_READY_TIMEOUT_S, True)],
            readiness_calls,
        )
        self.assertTrue(ctx.extra["gps_vehicle_readiness"]["ok"])

    def test_environment_readiness_failure_blocks_mission_adapter_installation(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_not_ready")
        master = _FakeMonitorConnection()

        def reject_initialising(
            master: Any,
            timeout_s: float,
            *,
            force_arm: bool,
        ) -> None:
            self.assertIsInstance(master, _FakeMonitorConnection)
            self.assertGreater(timeout_s, 0)
            self.assertTrue(force_arm)
            raise TimeoutError("vehicle remained INITIALISING")

        def factory(endpoint: str, *, timeout_s: float) -> _FakeMonitorConnection:
            self.assertTrue(endpoint)
            self.assertGreater(timeout_s, 0)
            return master

        env = GpsFailureEnvironment(
            GpsFailureConfig(launch_stack=True),
            mavlink_factory=factory,
            vehicle_readiness=reject_initialising,
        )

        with self.assertRaisesRegex(TimeoutError, "INITIALISING"):
            env.assert_ready(ctx.case, ctx)

        self.assertIs(ctx.extra["mavlink_master"], master)
        self.assertNotIn("mission_adapter", ctx.extra)
        self.assertNotIn("gps_vehicle_readiness", ctx.extra)

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

    def test_environment_cleanup_runs_governed_cleanup_then_scans(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_governed_cleanup")
        ctx.extra["gps_launch_plan"] = {"sitl_target": "plane-gps"}
        events: list[str] = []

        def governed_cleanup(*, timeout_s: float) -> dict[str, Any]:
            events.append(f"cleanup:{timeout_s}")
            return {
                "attempted": True,
                "ok": True,
                "returncode": 0,
            }

        def process_scanner() -> list[str]:
            events.append("scan")
            return []

        env = GpsFailureEnvironment(
            GpsFailureConfig(launch_stack=True, cleanup_timeout_s=2.5),
            governed_cleanup=governed_cleanup,
            process_scanner=process_scanner,
        )

        env.cleanup(ctx.case, ctx)

        self.assertEqual(["cleanup:2.5", "scan"], events)
        self.assertTrue(ctx.extra["gps_cleanup"]["ok"])
        self.assertEqual(
            0,
            ctx.extra["gps_cleanup"]["governed_cleanup"]["returncode"],
        )

    def test_environment_cleanup_fails_closed_on_governed_cleanup_error(self) -> None:
        ctx = _ctx(ROOT / "var" / "tmp_test_gps_phase2_governed_cleanup_error")
        ctx.extra["gps_launch_plan"] = {"sitl_target": "plane-gps"}
        env = GpsFailureEnvironment(
            GpsFailureConfig(launch_stack=True),
            governed_cleanup=lambda *, timeout_s: {
                "attempted": True,
                "ok": False,
                "returncode": 1,
                "error": "cleanup command exited with status 1",
            },
            process_scanner=lambda: [],
        )

        with self.assertRaisesRegex(RuntimeError, "governed_cleanup"):
            env.cleanup(ctx.case, ctx)

        self.assertFalse(ctx.extra["gps_cleanup"]["ok"])
        self.assertEqual(
            1,
            ctx.extra["gps_cleanup"]["governed_cleanup"]["returncode"],
        )

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
