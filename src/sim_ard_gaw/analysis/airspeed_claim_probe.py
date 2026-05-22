#!/usr/bin/env python3
"""
Focused probes for the 2026-03-24 airspeed investigation.

This script is intentionally split into two kinds of checks:
1. deterministic source-model calculations (`calc`, `check-doc`)
2. runtime isolation of the Gazebo plugin UDP output (`listen-json`)
"""

from __future__ import annotations

import argparse
import json
import math
import socket
import sys
from statistics import mean, pstdev
from typing import Any


SEA_LEVEL_AIR_DENSITY = 1.225
PLUGIN_AIR_DENSITY = 1.225
GRAVITY_MSS = 9.80665
R_SPECIFIC = 287.053072
RADIUS_EARTH_M = 6356.766e3

ATMOSPHERE_1976 = [
    {"amsl_m": -5000.0, "temp_K": 320.650, "pressure_Pa": 177687.0, "density": 1.930467, "temp_lapse": -6.5e-3},
    {"amsl_m": 11000.0, "temp_K": 216.650, "pressure_Pa": 22632.1, "density": 0.363918, "temp_lapse": 0.0},
    {"amsl_m": 20000.0, "temp_K": 216.650, "pressure_Pa": 5474.89, "density": 8.80349e-2, "temp_lapse": 1.0e-3},
    {"amsl_m": 32000.0, "temp_K": 228.650, "pressure_Pa": 868.019, "density": 1.32250e-2, "temp_lapse": 2.8e-3},
    {"amsl_m": 47000.0, "temp_K": 270.650, "pressure_Pa": 110.906, "density": 1.42753e-3, "temp_lapse": 0.0},
    {"amsl_m": 51000.0, "temp_K": 270.650, "pressure_Pa": 66.9389, "density": 8.61606e-4, "temp_lapse": -2.8e-3},
    {"amsl_m": 71000.0, "temp_K": 214.650, "pressure_Pa": 3.95642, "density": 6.42110e-5, "temp_lapse": -2.0e-3},
    {"amsl_m": 84852.0, "temp_K": 186.946, "pressure_Pa": 0.37338, "density": 6.95788e-6, "temp_lapse": 0.0},
]


def geometric_to_geopotential(alt_m: float) -> float:
    return (RADIUS_EARTH_M * alt_m) / (RADIUS_EARTH_M + alt_m)


def find_layer_by_altitude(alt_m: float) -> dict[str, float]:
    for idx in range(1, len(ATMOSPHERE_1976)):
        if alt_m < ATMOSPHERE_1976[idx]["amsl_m"]:
            return ATMOSPHERE_1976[idx - 1]
    return ATMOSPHERE_1976[-1]


def temperature_by_layer(alt_m: float, layer: dict[str, float]) -> float:
    lapse = layer["temp_lapse"]
    if lapse == 0.0:
        return layer["temp_K"]
    return layer["temp_K"] + lapse * (alt_m - layer["amsl_m"])


def density_for_alt_amsl(alt_m: float) -> float:
    geopotential_alt = geometric_to_geopotential(alt_m)
    layer = find_layer_by_altitude(geopotential_alt)
    lapse = layer["temp_lapse"]
    temp = temperature_by_layer(geopotential_alt, layer)

    if lapse == 0.0:
        fac = math.exp(-GRAVITY_MSS / (temp * R_SPECIFIC) * (geopotential_alt - layer["amsl_m"]))
        return layer["density"] * fac

    fac = GRAVITY_MSS / (lapse * R_SPECIFIC)
    temp_ratio = temp / layer["temp_K"]
    return layer["density"] * math.pow(temp_ratio, -(fac + 1.0))


def eas2tas_for_alt_amsl(alt_m: float) -> float:
    density = max(0.00001, density_for_alt_amsl(alt_m))
    return math.sqrt(SEA_LEVEL_AIR_DENSITY / density)


def plugin_airspeed_from_diff_pressure(diff_pressure_pa: float) -> float:
    if diff_pressure_pa <= 0.0:
        return 0.0
    return math.sqrt(2.0 * diff_pressure_pa / PLUGIN_AIR_DENSITY)


def sitl_eas_from_true_airspeed(true_airspeed_mps: float, alt_m: float) -> float:
    return true_airspeed_mps / eas2tas_for_alt_amsl(alt_m)


def sitl_raw_pressure_from_true_airspeed(true_airspeed_mps: float, alt_m: float, ratio: float) -> float:
    eas = sitl_eas_from_true_airspeed(true_airspeed_mps, alt_m)
    return (eas * eas) / ratio


def to_hpa(pressure_pa: float) -> float:
    return pressure_pa / 100.0


def parse_json_packet(packet: bytes) -> dict[str, Any]:
    text = packet.decode("utf-8", errors="replace").strip()
    return json.loads(text)


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def cmd_calc(args: argparse.Namespace) -> int:
    result: dict[str, Any] = {}

    if args.diff_pressure_pa is not None:
        result["plugin_from_diff_pressure"] = {
            "diff_pressure_pa": args.diff_pressure_pa,
            "airspeed_mps": plugin_airspeed_from_diff_pressure(args.diff_pressure_pa),
        }

    if args.true_airspeed_mps is not None:
        eas2tas = eas2tas_for_alt_amsl(args.altitude_m)
        eas = sitl_eas_from_true_airspeed(args.true_airspeed_mps, args.altitude_m)
        raw_pa = sitl_raw_pressure_from_true_airspeed(args.true_airspeed_mps, args.altitude_m, args.ratio)
        result["sitl_from_true_airspeed"] = {
            "true_airspeed_mps": args.true_airspeed_mps,
            "altitude_m": args.altitude_m,
            "ratio": args.ratio,
            "eas2tas": eas2tas,
            "expected_display_airspeed_mps": eas,
            "raw_pressure_pa": raw_pa,
            "raw_pressure_hpa": to_hpa(raw_pa),
        }

    if args.observed_raw_press is not None:
        result["observed_raw_press"] = {
            "input_value": args.observed_raw_press,
            "if_units_are_pa": {
                "pressure_pa": args.observed_raw_press,
                "plugin_equivalent_airspeed_mps": plugin_airspeed_from_diff_pressure(args.observed_raw_press),
            },
            "if_units_are_hpa": {
                "pressure_hpa": args.observed_raw_press,
                "pressure_pa": args.observed_raw_press * 100.0,
                "plugin_equivalent_airspeed_mps": plugin_airspeed_from_diff_pressure(args.observed_raw_press * 100.0),
            },
        }

    print_json(result)
    return 0


def cmd_check_doc(args: argparse.Namespace) -> int:
    plugin_airspeed = plugin_airspeed_from_diff_pressure(args.diff_pressure_pa)
    eas2tas = eas2tas_for_alt_amsl(args.altitude_m)
    expected_display = sitl_eas_from_true_airspeed(plugin_airspeed, args.altitude_m)
    raw_pa = sitl_raw_pressure_from_true_airspeed(plugin_airspeed, args.altitude_m, args.ratio)
    raw_hpa = to_hpa(raw_pa)

    report = {
        "scenario": {
            "diff_pressure_pa": args.diff_pressure_pa,
            "altitude_m": args.altitude_m,
            "ratio": args.ratio,
        },
        "what_the_plugin_should_send": {
            "json_airspeed_mps": plugin_airspeed,
        },
        "what_sitl_should_make_of_that": {
            "eas2tas": eas2tas,
            "display_airspeed_mps": expected_display,
            "raw_pressure_pa_internal": raw_pa,
            "raw_pressure_hpa_mavlink": raw_hpa,
        },
        "document_claims": {
            "negative_diff_pressure_zeroed_by_plugin": "supported",
            "positive_15p31_pa_implies_plugin_json_airspeed_about_5_mps": "supported",
            "same_case_should_show_ardupilot_raw_press_about_15p3_pa": "not_supported",
            "same_case_should_show_ardupilot_airspeed_about_5_mps": "not_supported",
            "reason": "SITL converts TAS to EAS with altitude and uses ARSPD_RATIO before reporting pressure/airspeed.",
        },
    }

    print_json(report)
    return 0


def cmd_listen_json(args: argparse.Namespace) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(args.timeout_s)
    sock.bind((args.host, args.port))

    captured = []
    try:
        while len(captured) < args.count:
            packet, addr = sock.recvfrom(65535)
            payload = parse_json_packet(packet)
            entry = {
                "from": {"host": addr[0], "port": addr[1]},
                "packet": payload,
            }
            captured.append(entry)
            if not args.quiet:
                print_json(entry)
    except socket.timeout:
        print(
            f"Timed out waiting for {args.count} packet(s) on {args.host}:{args.port}. "
            "Start Gazebo while this listener is running.",
            file=sys.stderr,
        )
        return 1
    finally:
        sock.close()

    if args.quiet:
        print_json({"captured": captured})

    return 0


def cmd_listen_json_stats(args: argparse.Namespace) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(args.timeout_s)
    sock.bind((args.host, args.port))

    airspeeds: list[float] = []
    packets_seen = 0
    first_packet: dict[str, Any] | None = None
    last_packet: dict[str, Any] | None = None

    try:
        while len(airspeeds) < args.count:
            packet, _addr = sock.recvfrom(65535)
            payload = parse_json_packet(packet)
            packets_seen += 1
            if first_packet is None:
                first_packet = payload
            last_packet = payload

            airspeed = payload.get("airspeed")
            if isinstance(airspeed, (int, float)):
                airspeeds.append(float(airspeed))
    except socket.timeout:
        print(
            f"Timed out waiting for {args.count} packet(s) with numeric airspeed on "
            f"{args.host}:{args.port}. Captured {len(airspeeds)} usable packets.",
            file=sys.stderr,
        )
        return 1
    finally:
        sock.close()

    summary = {
        "host": args.host,
        "port": args.port,
        "packets_seen": packets_seen,
        "airspeed_samples": len(airspeeds),
        "mean_airspeed_mps": mean(airspeeds),
        "stddev_airspeed_mps": pstdev(airspeeds),
        "min_airspeed_mps": min(airspeeds),
        "max_airspeed_mps": max(airspeeds),
    }

    if args.include_packets:
        summary["first_packet"] = first_packet
        summary["last_packet"] = last_packet

    print_json(summary)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Airspeed claim probes for the bench_s1 investigation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    calc = subparsers.add_parser("calc", help="Calculate plugin and SITL values for a chosen scenario")
    calc.add_argument("--diff-pressure-pa", type=float, default=None, help="Gazebo air_speed differential pressure in Pa")
    calc.add_argument("--true-airspeed-mps", type=float, default=None, help="JSON/plugin airspeed value in m/s")
    calc.add_argument("--altitude-m", type=float, default=584.0, help="AMSL altitude in meters")
    calc.add_argument("--ratio", type=float, default=1.99, help="ARSPD_RATIO / SITL airspeed ratio")
    calc.add_argument("--observed-raw-press", type=float, default=None, help="Observed MAVLink raw_press value to compare as Pa vs hPa")
    calc.set_defaults(func=cmd_calc)

    check_doc = subparsers.add_parser("check-doc", help="Run the document's default case through source-matched math")
    check_doc.add_argument("--diff-pressure-pa", type=float, default=15.31, help="Document diff_pressure case")
    check_doc.add_argument("--altitude-m", type=float, default=584.0, help="bench_s1 AMSL altitude")
    check_doc.add_argument("--ratio", type=float, default=1.99, help="Default ARSPD_RATIO")
    check_doc.set_defaults(func=cmd_check_doc)

    listen = subparsers.add_parser("listen-json", help="Listen for UDP JSON FDM packets from ArduPilotPlugin")
    listen.add_argument("--host", default="127.0.0.1", help="Bind host")
    listen.add_argument("--port", type=int, default=9002, help="Bind UDP port")
    listen.add_argument("--count", type=int, default=1, help="How many packets to capture")
    listen.add_argument("--timeout-s", type=float, default=15.0, help="Socket timeout in seconds")
    listen.add_argument("--quiet", action="store_true", help="Only print one final JSON blob")
    listen.set_defaults(func=cmd_listen_json)

    listen_stats = subparsers.add_parser(
        "listen-json-stats",
        help="Listen for UDP JSON FDM packets and summarize the airspeed field",
    )
    listen_stats.add_argument("--host", default="127.0.0.1", help="Bind host")
    listen_stats.add_argument("--port", type=int, default=9002, help="Bind UDP port")
    listen_stats.add_argument("--count", type=int, default=200, help="How many numeric airspeed samples to capture")
    listen_stats.add_argument("--timeout-s", type=float, default=30.0, help="Socket timeout in seconds")
    listen_stats.add_argument(
        "--include-packets",
        action="store_true",
        help="Include the first and last full packets in the JSON output",
    )
    listen_stats.set_defaults(func=cmd_listen_json_stats)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
