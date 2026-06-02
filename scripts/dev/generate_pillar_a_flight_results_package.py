#!/usr/bin/env python3
"""Generate Pillar A flight-results rollup artifacts from reviewed evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/pillar_a_mplconfig")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path("/home/ahmed/ardupilot_workspace_next")
OUT = ROOT / "evidence/curated_logs/pillar_a_flight_results_20260602"
TABLES = OUT / "tables"
PLOTS = OUT / "plots"


LANES = [
    {
        "lane": "Base plane",
        "targets": "plane + gazebo-plane",
        "status": "verified",
        "vehicle": "Mini Talon",
        "proof": "SITL/Gazebo/MAVLink handshake, GPS, EKF3, armed, physics coupling",
        "heartbeat_count": 256,
        "max_altitude_m": 0.20,
        "max_groundspeed_mps": 17.33,
        "sensor_or_bridge": "none",
        "evidence": "evidence/curated_logs/phase_2_runtime_2026-05-20/plane_evidence.txt",
    },
    {
        "lane": "CTE / airspeed",
        "targets": "plane-cte + gazebo-plane-cte",
        "status": "verified",
        "vehicle": "Mini Talon",
        "proof": "SITL/Gazebo/MAVLink handshake, GPS, EKF3, Armed AUTO, airborne CTE lane",
        "heartbeat_count": 126,
        "max_altitude_m": 46.86,
        "max_groundspeed_mps": 23.06,
        "sensor_or_bridge": "airspeed/wind lane",
        "evidence": "evidence/curated_logs/phase_2_runtime_2026-05-20/plane-cte_evidence.txt",
    },
    {
        "lane": "Plane LiDAR",
        "targets": "plane-lidar + gazebo-plane-lidar + bridge-plane",
        "status": "verified",
        "vehicle": "Mini Talon",
        "proof": "Airborne plane LiDAR lane plus Gazebo /lidar -> bridge -> MAVLink -> ArduPilot AGL readings",
        "heartbeat_count": 199,
        "max_altitude_m": 52.51,
        "max_groundspeed_mps": 22.37,
        "sensor_or_bridge": "bridge-plane AGL 1.83 m -> 35.60 m",
        "evidence": "evidence/curated_logs/phase_2_runtime_2026-05-20/plane-lidar_evidence.txt; evidence/curated_logs/phase_2_runtime_2026-05-20/bridge-plane_console.txt",
    },
    {
        "lane": "Copter base",
        "targets": "copter + gazebo-copter",
        "status": "verified",
        "vehicle": "Iris",
        "proof": "SITL/Gazebo/MAVLink handshake, GPS, EKF3, armed, takeoff 10 reached",
        "heartbeat_count": 201,
        "max_altitude_m": 10.02,
        "max_groundspeed_mps": 0.04,
        "sensor_or_bridge": "none",
        "evidence": "evidence/curated_logs/phase_2_runtime_2026-05-20/copter_evidence.txt",
    },
    {
        "lane": "Copter LiDAR",
        "targets": "copter-lidar + gazebo-copter-lidar + bridge-copter",
        "status": "verified with caveat",
        "vehicle": "Iris",
        "proof": "Copter LiDAR handshake and flight; bridge streamed 922 DISTANCE_SENSOR messages; obstacle return not captured",
        "heartbeat_count": 793,
        "max_altitude_m": 4.04,
        "max_groundspeed_mps": 2.46,
        "sensor_or_bridge": "bridge-copter 922 DISTANCE_SENSOR messages",
        "evidence": "evidence/curated_logs/phase_2_runtime_2026-05-20/copter-lidar_evidence.txt; evidence/curated_logs/phase_2_runtime_2026-05-20/bridge-copter_console.txt",
    },
    {
        "lane": "Staircase",
        "targets": "plane-staircase + gazebo-plane-staircase + bridge-plane",
        "status": "not yet tested",
        "vehicle": "Mini Talon",
        "proof": "Expansion lane present in lane map; no dated runtime proof yet",
        "heartbeat_count": None,
        "max_altitude_m": None,
        "max_groundspeed_mps": None,
        "sensor_or_bridge": "LiDAR overpass mission",
        "evidence": "docs/architecture/simulation_lanes.md",
    },
    {
        "lane": "Integrated airspeed+LiDAR",
        "targets": "plane-airspeed-lidar + gazebo-plane-airspeed-lidar + bridge-plane",
        "status": "not yet tested",
        "vehicle": "Mini Talon",
        "proof": "Expansion lane present in lane map; no dated runtime proof yet",
        "heartbeat_count": None,
        "max_altitude_m": None,
        "max_groundspeed_mps": None,
        "sensor_or_bridge": "airspeed + LiDAR integrated stack",
        "evidence": "docs/architecture/simulation_lanes.md",
    },
    {
        "lane": "Altitude-wind",
        "targets": "plane-altitude-wind + gazebo-plane-altitude-wind + wind-publisher-altitude",
        "status": "not yet tested",
        "vehicle": "Mini Talon",
        "proof": "Expansion lane present in lane map; no dated runtime proof yet",
        "heartbeat_count": None,
        "max_altitude_m": None,
        "max_groundspeed_mps": None,
        "sensor_or_bridge": "runtime wind-function proof lane",
        "evidence": "docs/architecture/simulation_lanes.md",
    },
    {
        "lane": "Rebuild",
        "targets": "plane-rebuild + gazebo-plane-rebuild",
        "status": "not yet tested",
        "vehicle": "Mini Talon",
        "proof": "Expansion lane present in lane map; no dated runtime proof yet",
        "heartbeat_count": None,
        "max_altitude_m": None,
        "max_groundspeed_mps": None,
        "sensor_or_bridge": "incremental wind/airspeed investigation",
        "evidence": "docs/architecture/simulation_lanes.md",
    },
    {
        "lane": "Bench",
        "targets": "gazebo-plane-bench and related",
        "status": "not a flight lane",
        "vehicle": "Mini Talon",
        "proof": "Bench worlds are isolation harnesses, not flight-ready operating worlds",
        "heartbeat_count": None,
        "max_altitude_m": None,
        "max_groundspeed_mps": None,
        "sensor_or_bridge": "manual sensor experiment harness",
        "evidence": "docs/architecture/simulation_lanes.md",
    },
]


ANALYSIS_RESULT = {
    "result": "CTE wind-envelope",
    "status": "verified",
    "report": "evidence/reports/features/2026-06-02_cte_wind_envelope_result.md",
    "curated_package": "evidence/curated_logs/cte_wind_envelope_017_20260602/",
    "accepted_runs": 32,
    "accepted_cells": 13,
    "matrix_cells": 16,
    "no_accepted_edge_cells": 3,
    "calm_square_rms_m": 7.15,
    "worst_accepted_square_rms_m": 17.99,
    "component_interaction_r2": 0.751,
    "ekf_wind_audit_named_bins_accepted": 38,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv() -> None:
    fieldnames = list(LANES[0].keys())
    with (TABLES / "pillar_a_lane_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(LANES)


def write_markdown() -> None:
    lines = [
        "# Pillar A Flight-Lane And Analysis Summary",
        "",
        "Scope: rollup of already-reviewed flight-lane and analysis evidence. No new SITL/Gazebo runs.",
        "",
        "## Verified Core Flight Lanes",
        "",
        "| Lane | Targets | Proof | Heartbeats | Max altitude m | Max groundspeed m/s | Evidence |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for lane in LANES:
        if not lane["status"].startswith("verified"):
            continue
        lines.append(
            f"| {lane['lane']} | `{lane['targets']}` | {lane['proof']} | "
            f"{lane['heartbeat_count']} | {lane['max_altitude_m']:.2f} | "
            f"{lane['max_groundspeed_mps']:.2f} | {lane['evidence']} |"
        )
    lines.extend(
        [
            "",
            "## Expansion Lane Boundary",
            "",
            "| Lane | Targets | Current status | Boundary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for lane in LANES:
        if lane["status"].startswith("verified"):
            continue
        lines.append(f"| {lane['lane']} | `{lane['targets']}` | {lane['status']} | {lane['proof']} |")
    lines.extend(
        [
            "",
            "## Analysis Result",
            "",
            "| Result | Status | Headline | Evidence |",
            "| --- | --- | --- | --- |",
            (
                f"| {ANALYSIS_RESULT['result']} | {ANALYSIS_RESULT['status']} | "
                f"{ANALYSIS_RESULT['accepted_runs']} accepted runs, "
                f"{ANALYSIS_RESULT['accepted_cells']}/{ANALYSIS_RESULT['matrix_cells']} cells accepted, "
                f"{ANALYSIS_RESULT['no_accepted_edge_cells']} envelope-edge no-accepted cells, "
                f"calm RMS {ANALYSIS_RESULT['calm_square_rms_m']:.2f} m, "
                f"worst accepted RMS {ANALYSIS_RESULT['worst_accepted_square_rms_m']:.2f} m, "
                f"component+interaction R2 {ANALYSIS_RESULT['component_interaction_r2']:.3f}. | "
                f"{ANALYSIS_RESULT['report']} |"
            ),
        ]
    )
    (TABLES / "pillar_a_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json() -> None:
    verified = [lane for lane in LANES if lane["status"].startswith("verified")]
    not_tested = [lane for lane in LANES if lane["status"] == "not yet tested"]
    data = {
        "date_curated": "2026-06-02",
        "scope": "Pillar A flight engineering and analysis results rollup",
        "live_runs_performed": False,
        "headline": {
            "verified_core_flight_lane_count": len(verified),
            "flight_lane_map_count": len(LANES),
            "not_yet_tested_expansion_lane_count": len(not_tested),
            "bench_is_not_flight_lane": True,
            "analysis_result": ANALYSIS_RESULT,
        },
        "lanes": LANES,
        "source_reports": [
            "evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md",
            "evidence/reports/features/2026-06-02_cte_wind_envelope_result.md",
            "docs/architecture/simulation_lanes.md",
            "docs/vehicles/status.md",
            "docs/operations/launch_targets.md",
        ],
        "old_workspace_modified": False,
    }
    (OUT / "pillar_a_metrics.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def plot_lane_status() -> None:
    labels = [lane["lane"] for lane in LANES]
    status_map = {
        "verified": 3,
        "verified with caveat": 2,
        "not yet tested": 1,
        "not a flight lane": 0,
    }
    values = [status_map[lane["status"]] for lane in LANES]
    colors = {
        3: "#009E73",
        2: "#E69F00",
        1: "#9E9E9E",
        0: "#5E5E5E",
    }
    fig, ax = plt.subplots(figsize=(11.5, 6.4), constrained_layout=True)
    y = np.arange(len(labels))
    ax.barh(y, values, color=[colors[v] for v in values], height=0.66)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 3.4)
    ax.set_xticks([0, 1, 2, 3], ["not flight", "not tested", "verified caveat", "verified"])
    ax.set_title("Pillar A lane map: verified core plus honest expansion boundary", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#E6E6E6")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for i, lane in enumerate(LANES):
        if lane["status"].startswith("verified"):
            note = f"{lane['heartbeat_count']} heartbeats"
        else:
            note = lane["status"]
        ax.text(values[i] + 0.05, i, note, va="center", fontsize=9)
    for ext in ("png", "svg"):
        fig.savefig(PLOTS / f"pillar_a_lane_status.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_readme() -> None:
    text = f"""# Pillar A Flight Results Rollup

Date curated: 2026-06-02

Scope: presentation-ready rollup for Pillar A, using existing reviewed evidence
only. No live SITL/Gazebo runs were performed for this package.

## Boundary

Pillar A is complete as:

- 5 verified core flight lanes backed by Phase 2 dated runtime evidence.
- 1 deep analysis result: the production-like CTE wind-envelope package.
- An honest 10-row lane map that separates verified lanes from expansion lanes
  that are not yet runtime-tested.

Pillar A is not claimed as 10 verified flight lanes. `Bench` is explicitly not
a flight lane, and `staircase`, `integrated airspeed+LiDAR`, `altitude-wind`,
and `rebuild` remain expansion lanes without dated runtime proof.

## Contents

- `pillar_a_metrics.json` - machine-readable rollup.
- `tables/pillar_a_summary.md` - human-readable lane and analysis table.
- `tables/pillar_a_lane_summary.csv` - lane table.
- `plots/pillar_a_lane_status.png` and `.svg` - deck-ready status map.
- `written_conclusion.md` - executive/technical conclusion for Pillar A.

## Source Evidence

- Phase 2 runtime parity:
  `evidence/reports/migration/PHASE_2_RUNTIME_PARITY_2026-05-20.md`
- Phase 2 curated per-target captures:
  `evidence/curated_logs/phase_2_runtime_2026-05-20/`
- CTE wind-envelope package:
  `evidence/curated_logs/cte_wind_envelope_017_20260602/`
- CTE wind-envelope report:
  `evidence/reports/features/2026-06-02_cte_wind_envelope_result.md`
- Lane status docs:
  `docs/architecture/simulation_lanes.md`,
  `docs/vehicles/status.md`,
  `docs/operations/launch_targets.md`

## Generation Script

- Path: `scripts/dev/generate_pillar_a_flight_results_package.py`
- SHA256: `{sha256(Path(__file__))}`
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def write_conclusion() -> None:
    text = """# Pillar A Conclusion - Flight Engineering And Analysis Results

Pillar A is presentation-ready when scoped to what the workspace has already
proved: verified core flight lanes plus the deep CTE wind-envelope analysis.
The result is not one anecdote. The workspace has dated runtime evidence for
five core lanes: base plane, CTE/airspeed plane, plane LiDAR, copter base, and
copter LiDAR. Those lanes cover two vehicles, fixed-wing and multirotor, and
multiple integration paths: plain SITL/Gazebo/MAVLink flight, wind/airspeed
operation, LiDAR bridge integration, logger output, and cleanup behavior.

The analysis result is the production-like CTE wind envelope. It turns the CTE
lane from a launch smoke proof into a real engineering result: 32 accepted runs,
13 of 16 accepted wind cells, 3 no-accepted high-wind envelope-edge cells, calm
square RMS 7.15 m, worst accepted RMS 17.99 m, and a component+interaction wind
model with R2 0.751. The internal EKF wind audit accepted all 38 named BINs, so
the envelope edge is valid wind behavior rather than a harness defect.

The honest boundary is just as important. Pillar A should not claim 10 verified
flight lanes. The lane map has 10 rows, but four are expansion lanes without
dated runtime proof, and bench is explicitly not a flight lane. Copter LiDAR is
verified for handshake, flight, and bridge message flow; obstacle return remains
uncaptured. This is a strong pillar because it is precise: the proven core is
real, and the remaining expansion surface is named without exaggeration.
"""
    (OUT / "written_conclusion.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    write_csv()
    write_markdown()
    write_json()
    plot_lane_status()
    write_conclusion()
    write_readme()


if __name__ == "__main__":
    main()
