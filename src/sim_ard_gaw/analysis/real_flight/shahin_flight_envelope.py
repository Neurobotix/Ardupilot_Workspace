#!/usr/bin/env python3
"""Extract the flight envelope of a real ArduPlane DataFlash log.

Purpose: give the numbers a SITL model must reproduce to "fly like" the real
aircraft (GPS-denied navigation study, Shahin-E model build).

Outputs (in --out):
  params_full.parm      every parameter in the log (load-ready for SITL)
  params_key.json       the parameters that matter for the model build
  level_bins.csv        straight-and-level flight, binned by airspeed
  turns.csv             steady turns, binned by bank angle
  climbs_glides.csv     climb / descent segments
  wind.csv              wind estimate per 5 minutes (GPS minus air vector)
  summary.json          everything above in one file
  summary.md            human-readable table

Usage (from the workspace root, inside env/):
  python src/sim_ard_gaw/analysis/real_flight/shahin_flight_envelope.py \
      var/real_flights/2025-12-30_094938_shahin_e.bin \
      --out var/analysis/shahin_e_flight_envelope_20261012
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from pymavlink import mavutil

G = 9.80665
GRID_HZ = 2.0

PLANE_MODES = {
    0: "MANUAL", 1: "CIRCLE", 2: "STABILIZE", 3: "TRAINING", 4: "ACRO",
    5: "FBWA", 6: "FBWB", 7: "CRUISE", 8: "AUTOTUNE", 10: "AUTO", 11: "RTL",
    12: "LOITER", 13: "TAKEOFF", 14: "AVOID_ADSB", 15: "GUIDED",
}
# Modes where the autopilot holds speed/altitude, so level flight is "trimmed".
AUTOPILOT_MODES = {1, 6, 7, 10, 11, 12, 15}

WANTED = ["PARM", "MODE", "ATT", "CTUN", "ARSP", "BARO", "GPS", "POS",
          "BAT", "RCOU", "TECS"]

KEY_PARAM_PREFIXES = (
    "AIRSPEED_", "ARSPD_", "TRIM_", "THR_", "TECS_", "ROLL_LIMIT", "LIM_",
    "PTCH_LIM", "PTCH2SRV", "RLL2SRV", "RLL_RATE", "PTCH_RATE", "YAW_RATE",
    "KFF_", "FLAP_", "TKOFF_", "LAND_", "SERVO", "BATT_", "EK3_", "AHRS_",
    "COMPASS_", "INS_", "STALL_", "NAVL1_", "WP_", "RTL_", "SCALING_SPEED",
    "STAB_PITCH_DOWN", "MIXING_", "FRAME_", "Q_ENABLE", "LOG_",
)


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------
def read_log(path: Path):
    """Return (series, params, modes). series[msg][field] -> np.array."""
    mlog = mavutil.mavlink_connection(str(path), dialect="ardupilotmega")
    raw: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    params: dict[str, float] = {}
    modes: list[tuple[float, int]] = []
    count = 0
    while True:
        m = mlog.recv_match(type=WANTED)
        if m is None:
            break
        count += 1
        t = m.get_type()
        d = m.to_dict()
        if t == "PARM":
            params[d["Name"]] = float(d["Value"])
            continue
        tus = d.get("TimeUS")
        if tus is None:
            continue
        ts = tus / 1e6
        if t == "MODE":
            modes.append((ts, int(d.get("ModeNum", d.get("Mode", -1)))))
            continue
        # Keep only the primary instance of multi-instance messages.
        inst = d.get("I", d.get("Instance", 0))
        if t in ("ARSP", "BARO", "GPS", "BAT") and inst not in (0, None):
            continue
        raw[t]["t"].append(ts)
        for k, v in d.items():
            if isinstance(v, (int, float)) and k not in ("TimeUS", "mavpackettype"):
                raw[t][k].append(float(v))
        if count % 500000 == 0:
            print(f"  read {count:,} messages", file=sys.stderr)
    series = {t: {k: np.asarray(v) for k, v in f.items()} for t, f in raw.items()}
    return series, params, modes


def field(series, msg, *names):
    """First existing (time, values) pair for msg among candidate field names."""
    s = series.get(msg)
    if not s:
        return None
    for n in names:
        if n in s and len(s[n]) == len(s["t"]) and len(s["t"]) > 1:
            return s["t"], s[n]
    return None


# --------------------------------------------------------------------------
# Pure helpers (unit-testable)
# --------------------------------------------------------------------------
def resample(t_src, v_src, grid, angle=False):
    order = np.argsort(t_src)
    t_src, v_src = t_src[order], v_src[order]
    if angle:
        v_src = np.unwrap(np.radians(v_src))
        return np.degrees(np.interp(grid, t_src, v_src))
    return np.interp(grid, t_src, v_src, left=np.nan, right=np.nan)


def smooth(x, seconds):
    """Centered moving average over `seconds`, NaN-safe."""
    n = max(1, int(round(seconds * GRID_HZ)))
    if n == 1:
        return x
    ok = np.isfinite(x)
    k = np.ones(n)
    num = np.convolve(np.where(ok, x, 0.0), k, mode="same")
    den = np.convolve(ok.astype(float), k, mode="same")
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def mode_on_grid(grid, modes):
    out = np.full(grid.shape, -1, dtype=int)
    for ts, mode in sorted(modes):
        out[grid >= ts] = mode
    return out


def runs(mask, min_len):
    """Yield (start, stop) index pairs where mask is True for >= min_len samples."""
    idx = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(int), [0]))))
    for a, b in zip(idx[::2], idx[1::2]):
        if b - a >= min_len:
            yield a, b


def stats(x):
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"n": 0}
    return {"n": int(x.size), "median": round(float(np.median(x)), 3),
            "p10": round(float(np.percentile(x, 10)), 3),
            "p90": round(float(np.percentile(x, 90)), 3)}


def wind_from_vectors(gs_n, gs_e, tas, yaw_deg):
    """Wind = ground velocity - air velocity (no sideslip assumed)."""
    yaw = np.radians(yaw_deg)
    wn = gs_n - tas * np.cos(yaw)
    we = gs_e - tas * np.sin(yaw)
    return wn, we


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------
def build_grid(series, modes):
    att = field(series, "ATT", "Roll")
    if att is None:
        raise SystemExit("No ATT messages: cannot analyse.")
    t0, t1 = att[0].min(), att[0].max()
    grid = np.arange(t0, t1, 1.0 / GRID_HZ)
    g = {"t": grid}

    def put(name, src, angle=False):
        if src is not None:
            g[name] = resample(src[0], src[1], grid, angle=angle)

    put("roll", att)
    put("pitch", field(series, "ATT", "Pitch"))
    put("yaw", field(series, "ATT", "Yaw"), angle=True)
    put("thr", field(series, "CTUN", "ThO", "ThrOut"))
    put("aspd_ctun", field(series, "CTUN", "As", "Aspd"))
    put("aspd", field(series, "ARSP", "Airspeed"))
    put("climb_baro", field(series, "BARO", "CRt"))
    put("alt_rel", field(series, "POS", "RelHomeAlt"))
    put("alt_baro", field(series, "BARO", "Alt"))
    put("gspd", field(series, "GPS", "Spd"))
    put("gcrs", field(series, "GPS", "GCrs"), angle=True)
    put("gvz", field(series, "GPS", "VZ"))
    put("volt", field(series, "BAT", "Volt", "Volts"))
    put("curr", field(series, "BAT", "Curr"))
    put("eas_dem", field(series, "TECS", "spdem"))

    if "aspd" not in g and "aspd_ctun" in g:
        g["aspd"] = g["aspd_ctun"]
    if "gvz" in g:
        g["climb"] = smooth(-g["gvz"], 5.0)
    elif "climb_baro" in g:
        g["climb"] = smooth(g["climb_baro"], 5.0)
    if "alt_rel" not in g and "alt_baro" in g:
        g["alt_rel"] = g["alt_baro"]
    if "yaw" in g:
        g["yaw_rate"] = smooth(np.gradient(g["yaw"], 1.0 / GRID_HZ), 3.0)
    if "roll" in g:
        g["roll"] = smooth(g["roll"], 2.0)
    if "volt" in g and "curr" in g:
        g["power_w"] = g["volt"] * g["curr"]
    g["mode"] = mode_on_grid(grid, modes)
    return g


def airborne_mask(g):
    m = np.ones(g["t"].shape, bool)
    if "gspd" in g:
        m &= g["gspd"] > 8
    if "alt_rel" in g:
        m &= g["alt_rel"] > 20
    if "aspd" in g:
        m &= g["aspd"] > 8
    return m


def level_flight(g, air):
    need = ("roll", "climb", "aspd", "yaw_rate")
    if not all(k in g for k in need):
        return [], None
    mask = (air & (np.abs(g["roll"]) < 5) & (np.abs(g["climb"]) < 1.0)
            & (np.abs(g["yaw_rate"]) < 3) & np.isin(g["mode"], list(AUTOPILOT_MODES)))
    sel = np.zeros_like(mask)
    for a, b in runs(mask, int(10 * GRID_HZ)):
        sel[a:b] = True
    rows = []
    if sel.sum() == 0:
        return rows, sel
    aspd = g["aspd"][sel]
    for lo in np.arange(np.floor(aspd.min()), np.floor(aspd.max()) + 1, 1.0):
        b = sel & (g["aspd"] >= lo) & (g["aspd"] < lo + 1)
        if b.sum() < 20:
            continue
        row = {"airspeed_bin_mps": f"{lo:.0f}-{lo+1:.0f}", "seconds": round(float(b.sum()) / GRID_HZ, 1)}
        for k, label in (("thr", "throttle_pct"), ("pitch", "pitch_deg"),
                         ("curr", "current_a"), ("power_w", "power_w")):
            if k in g:
                row[label] = round(float(np.nanmedian(g[k][b])), 2)
        rows.append(row)
    return rows, sel


def turns(g, air):
    need = ("roll", "aspd", "yaw_rate", "climb")
    if not all(k in g for k in need):
        return []
    rows = []
    steady = air & (np.abs(g["climb"]) < 1.5) & np.isin(g["mode"], list(AUTOPILOT_MODES))
    for lo in (5, 10, 15, 20, 25, 30, 35, 40):
        b = steady & (np.abs(g["roll"]) >= lo) & (np.abs(g["roll"]) < lo + 5)
        sel = np.zeros_like(b)
        for a, c in runs(b, int(3 * GRID_HZ)):
            sel[a:c] = True
        if sel.sum() < 10:
            continue
        phi = np.radians(np.abs(g["roll"][sel]))
        v = g["aspd"][sel]
        expected = np.degrees(G * np.tan(phi) / v)
        row = {"bank_bin_deg": f"{lo}-{lo+5}", "seconds": round(float(sel.sum()) / GRID_HZ, 1),
               "airspeed_mps": round(float(np.median(v)), 2),
               "turn_rate_dps": round(float(np.median(np.abs(g["yaw_rate"][sel]))), 2),
               "coordinated_rate_dps": round(float(np.median(expected)), 2)}
        if "thr" in g:
            row["throttle_pct"] = round(float(np.nanmedian(g["thr"][sel])), 2)
        if "pitch" in g:
            row["pitch_deg"] = round(float(np.nanmedian(g["pitch"][sel])), 2)
        rows.append(row)
    return rows


def climbs_glides(g, air):
    need = ("climb", "aspd", "roll")
    if not all(k in g for k in need):
        return []
    rows = []
    wings_level = air & (np.abs(g["roll"]) < 10)
    cases = [("climb", g["climb"] > 0.8)]
    if "thr" in g:
        cases.append(("glide_throttle_below_5pct", (g["climb"] < -0.4) & (g["thr"] < 5)))
        cases.append(("powered_descent", (g["climb"] < -0.4) & (g["thr"] >= 5)))
    for name, cond in cases:
        sel = np.zeros_like(cond)
        for a, b in runs(wings_level & cond, int(3 * GRID_HZ)):
            sel[a:b] = True
        if sel.sum() < 10:
            continue
        row = {"segment": name, "seconds": round(float(sel.sum()) / GRID_HZ, 1),
               "climb_rate_mps": round(float(np.median(g["climb"][sel])), 2),
               "airspeed_mps": round(float(np.median(g["aspd"][sel])), 2)}
        for k, label in (("thr", "throttle_pct"), ("pitch", "pitch_deg"), ("power_w", "power_w")):
            if k in g:
                row[label] = round(float(np.nanmedian(g[k][sel])), 2)
        if name.startswith("glide"):
            sink = -row["climb_rate_mps"]
            row["glide_ratio"] = round(math.sqrt(max(row["airspeed_mps"] ** 2 - sink ** 2, 0)) / sink, 1)
        rows.append(row)
    return rows


def wind(g, air):
    need = ("gspd", "gcrs", "aspd", "yaw")
    if not all(k in g for k in need):
        return []
    crs = np.radians(g["gcrs"])
    wn, we = wind_from_vectors(g["gspd"] * np.cos(crs), g["gspd"] * np.sin(crs), g["aspd"], g["yaw"])
    ok = air & (np.abs(g["roll"]) < 10)
    rows = []
    t0 = g["t"][0]
    for start in np.arange(t0, g["t"][-1], 300):
        b = ok & (g["t"] >= start) & (g["t"] < start + 300)
        if b.sum() < 60:
            continue
        n, e = float(np.median(wn[b])), float(np.median(we[b]))
        rows.append({"minute": round(float(start - t0) / 60, 1),
                     "wind_speed_mps": round(math.hypot(n, e), 2),
                     "wind_from_deg": round((math.degrees(math.atan2(e, n)) + 180) % 360, 0)})
    return rows


def write_csv(path, rows):
    if not rows:
        path.write_text("no data\n")
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def md_table(rows):
    if not rows:
        return "_no data_\n"
    keys = list(dict.fromkeys(k for r in rows for k in r))
    out = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(k, "")) for k in keys) + " |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bin", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"Reading {args.bin} ...", file=sys.stderr)
    series, params, modes = read_log(args.bin)
    g = build_grid(series, modes)
    air = airborne_mask(g)

    with (args.out / "params_full.parm").open("w") as f:
        for k in sorted(params):
            f.write(f"{k},{params[k]:g}\n")
    key_params = {k: v for k, v in sorted(params.items()) if k.startswith(KEY_PARAM_PREFIXES)}
    servo_fn = {k: v for k, v in key_params.items() if k.endswith("_FUNCTION") and v != 0}
    (args.out / "params_key.json").write_text(json.dumps(key_params, indent=1))

    level_rows, level_sel = level_flight(g, air)
    turn_rows = turns(g, air)
    cg_rows = climbs_glides(g, air)
    wind_rows = wind(g, air)

    mode_time = defaultdict(float)
    for m in g["mode"][air]:
        mode_time[PLANE_MODES.get(int(m), str(int(m)))] += 1.0 / GRID_HZ

    overview = {
        "log": args.bin.name,
        "messages_found": sorted(series),
        "messages_missing": sorted(set(WANTED) - set(series) - {"PARM", "MODE"}),
        "params_found": len(params),
        "airborne_minutes": round(air.sum() / GRID_HZ / 60, 1),
        "airborne_minutes_by_mode": {k: round(v / 60, 1) for k, v in sorted(mode_time.items())},
        "airborne_airspeed_mps": stats(g["aspd"][air]) if "aspd" in g else None,
        "airborne_altitude_rel_m": stats(g["alt_rel"][air]) if "alt_rel" in g else None,
        "level_flight_minutes": round(float(level_sel.sum()) / GRID_HZ / 60, 1) if level_sel is not None else 0,
        "servo_functions": servo_fn,
        "airborne_distributions": {
            k: stats(np.abs(g[k][air]) if k in ("roll", "yaw_rate") else g[k][air])
            for k in ("roll", "climb", "yaw_rate", "thr", "pitch") if k in g
        },
    }
    summary = {"overview": overview, "level_bins": level_rows, "turns": turn_rows,
               "climbs_glides": cg_rows, "wind_5min": wind_rows}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1))
    write_csv(args.out / "level_bins.csv", level_rows)
    write_csv(args.out / "turns.csv", turn_rows)
    write_csv(args.out / "climbs_glides.csv", cg_rows)
    write_csv(args.out / "wind.csv", wind_rows)

    md = [f"# Flight envelope: {args.bin.name}\n",
          "```json\n" + json.dumps(overview, indent=1) + "\n```\n",
          "## Straight and level (autopilot modes, held >= 10 s)\n", md_table(level_rows),
          "## Steady turns\n", md_table(turn_rows),
          "## Climbs and descents\n", md_table(cg_rows),
          "## Wind (5-minute medians)\n", md_table(wind_rows)]
    (args.out / "summary.md").write_text("\n".join(md))
    print(f"Done. Outputs in {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
