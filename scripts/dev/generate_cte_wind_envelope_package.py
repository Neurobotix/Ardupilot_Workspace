#!/usr/bin/env python3
"""Generate the curated CTE wind-envelope analysis package.

Inputs are read-only 020 postprocessing tables from the deprecated reference
workspace. Outputs are written into this workspace's curated evidence home.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "var/analysis/cte_wind_envelope_017_20260602/mplconfig")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path("/home/ahmed/ardupilot_workspace_next")
SOURCE_ROOT = Path(
    "/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs"
    "/020_Old_Param_Fixed_CTE_Report/summary/corrected"
)
DATASET_ROOT = Path(
    "/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs"
    "/017_params_old_009_matrix_r3_plugin_fixed"
)
OUT = REPO_ROOT / "evidence/curated_logs/cte_wind_envelope_017_20260602"
PLOTS = OUT / "plots"
TABLES = OUT / "tables"

WINDS = [0, 4, 8, 12]
CRUISE_MPS = 14.0

COLORS = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "gray": "#666666",
    "light_gray": "#F4F4F4",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def finite_or_none(value):
    if value is None:
        return None
    try:
        if math.isnan(float(value)):
            return None
    except (TypeError, ValueError):
        return value
    return float(value)


def fmt(value, digits=2) -> str:
    value = finite_or_none(value)
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def text_or_dash(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and math.isnan(value):
        return "-"
    return str(value)


def model_fit(df: pd.DataFrame, columns: list[str], y_col: str):
    x = np.column_stack([np.ones(len(df))] + [df[col].to_numpy(float) for col in columns])
    y = df[y_col].to_numpy(float)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    pred = x @ coef
    residual = y - pred
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot
    return {
        "intercept": float(coef[0]),
        "coefficients": {name: float(value) for name, value in zip(columns, coef[1:])},
        "r2": r2,
        "rmse_m": float(np.sqrt(np.mean(residual**2))),
        "mean_abs_residual_m": float(np.mean(np.abs(residual))),
        "predicted": pred,
        "residual": residual,
    }


def adjacent_monotonicity(combo_df: pd.DataFrame, metric: str) -> dict:
    rows = []
    cols = []
    for y in WINDS:
        values = {
            int(row.x_wind_mps): float(getattr(row, metric))
            for row in combo_df[combo_df.y_wind_mps == y].itertuples()
            if finite_or_none(getattr(row, metric)) is not None
        }
        for a, b in zip(WINDS, WINDS[1:]):
            if a in values and b in values:
                rows.append({"fixed_y": y, "from_x": a, "to_x": b, "nondecreasing": values[b] >= values[a]})
    for x in WINDS:
        values = {
            int(row.y_wind_mps): float(getattr(row, metric))
            for row in combo_df[combo_df.x_wind_mps == x].itertuples()
            if finite_or_none(getattr(row, metric)) is not None
        }
        for a, b in zip(WINDS, WINDS[1:]):
            if a in values and b in values:
                cols.append({"fixed_x": x, "from_y": a, "to_y": b, "nondecreasing": values[b] >= values[a]})
    all_pairs = rows + cols
    passed = sum(1 for item in all_pairs if item["nondecreasing"])
    return {
        "accepted_adjacent_pair_count": len(all_pairs),
        "nondecreasing_pair_count": passed,
        "nondecreasing_fraction": passed / len(all_pairs),
        "row_pairs": rows,
        "column_pairs": cols,
    }


def grid_from(combo_df: pd.DataFrame, metric: str):
    grid = np.full((len(WINDS), len(WINDS)), np.nan)
    for _, row in combo_df.iterrows():
        x = WINDS.index(int(row["x_wind_mps"]))
        y = WINDS.index(int(row["y_wind_mps"]))
        grid[y, x] = float(row[metric])
    return grid


def outcome_grid(outcome_df: pd.DataFrame):
    order = {
        "accepted_only": 2,
        "partial_failure_with_accepted": 1,
        "failure_no_accepted": 0,
    }
    grid = np.full((len(WINDS), len(WINDS)), np.nan)
    labels = [["" for _ in WINDS] for _ in WINDS]
    for _, row in outcome_df.iterrows():
        x = WINDS.index(int(row["x_wind_mps"]))
        y = WINDS.index(int(row["y_wind_mps"]))
        grid[y, x] = order[row["outcome"]]
        accepted = int(row["accepted_run_count"])
        attempts = int(row["attempt_count"])
        if row["outcome"] == "failure_no_accepted":
            labels[y][x] = f"0/{attempts}\nedge"
        elif row["outcome"] == "partial_failure_with_accepted":
            labels[y][x] = f"{accepted}/{attempts}\npartial"
        else:
            labels[y][x] = f"{accepted}/{attempts}"
    return grid, labels


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, color="#E6E6E6", linewidth=0.8, zorder=0)


def heatmap(
    grid,
    title,
    cbar_label,
    filename,
    cmap="viridis",
    annotate=None,
    value_fmt="{:.1f}",
    missing_label="No accepted\nrun",
):
    fig, ax = plt.subplots(figsize=(8.0, 6.2), constrained_layout=True)
    masked = np.ma.masked_invalid(grid)
    cmap_obj = plt.get_cmap(cmap).copy()
    cmap_obj.set_bad("#F0F0F0")
    im = ax.imshow(masked, origin="lower", cmap=cmap_obj)
    cbar = fig.colorbar(im, ax=ax, shrink=0.86)
    cbar.set_label(cbar_label)
    ax.set_xticks(range(len(WINDS)), [str(v) for v in WINDS])
    ax.set_yticks(range(len(WINDS)), [str(v) for v in WINDS])
    ax.set_xlabel("East wind component (m/s)")
    ax.set_ylabel("North wind component (m/s)")
    ax.set_title(title, loc="left", fontweight="bold")
    for yi in range(len(WINDS)):
        for xi in range(len(WINDS)):
            if np.isnan(grid[yi, xi]):
                text = missing_label
                color = "#333333"
            else:
                text = annotate[yi][xi] if annotate else value_fmt.format(grid[yi, xi])
                color = "white" if grid[yi, xi] > np.nanmax(grid) * 0.62 else "#111111"
            ax.text(xi, yi, text, ha="center", va="center", fontsize=10, color=color)
    for ext in ("png", "svg"):
        fig.savefig(PLOTS / f"{filename}.{ext}", dpi=220)
    plt.close(fig)


def outcome_heatmap(outcome_df: pd.DataFrame):
    from matplotlib.colors import ListedColormap, BoundaryNorm

    grid, labels = outcome_grid(outcome_df)
    cmap = ListedColormap([COLORS["red"], COLORS["orange"], COLORS["green"]])
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)
    fig, ax = plt.subplots(figsize=(9.2, 7.0), constrained_layout=True)
    ax.imshow(grid, origin="lower", cmap=cmap, norm=norm)
    ax.set_xticks(range(len(WINDS)), [str(v) for v in WINDS])
    ax.set_yticks(range(len(WINDS)), [str(v) for v in WINDS])
    ax.set_xlabel("East wind component (m/s)")
    ax.set_ylabel("North wind component (m/s)")
    ax.set_title("Production-like CTE campaign outcome map", loc="left", fontweight="bold")
    ax.text(
        0,
        1.04,
        "Cell label = accepted attempts / total attempts. No-accepted cells are envelope edge, not interpolated CTE.",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9.5,
        color="#333333",
    )
    for yi in range(len(WINDS)):
        for xi in range(len(WINDS)):
            ax.text(xi, yi, labels[yi][xi], ha="center", va="center", fontsize=10, color="white", fontweight="bold")
    handles = [
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=COLORS["green"], markersize=12, label="Accepted-only"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=COLORS["orange"], markersize=12, label="Partial failure with accepted"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=COLORS["red"], markersize=12, label="Failure, no accepted run"),
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.24), ncol=3, frameon=False)
    for ext in ("png", "svg"):
        fig.savefig(PLOTS / f"campaign_outcome_envelope_heatmap.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def trend_plot(combo_df: pd.DataFrame, fit: dict, magnitude_fit: dict):
    fig, (ax, axr) = plt.subplots(
        2,
        1,
        figsize=(8.6, 7.4),
        constrained_layout=True,
        gridspec_kw={"height_ratios": [3.0, 1.1]},
    )
    sizes = 48 + combo_df["replicate_count"].to_numpy(float) * 28
    sc = ax.scatter(
        combo_df["wind_magnitude_mps"],
        combo_df["square_rms_true_path_dev_mean_m"],
        c=combo_df["x_wind_mps"],
        s=sizes,
        cmap="viridis",
        edgecolor="#222222",
        linewidth=0.7,
        zorder=3,
    )
    x_line = np.linspace(0, combo_df["wind_magnitude_mps"].max(), 100)
    y_line = magnitude_fit["intercept"] + magnitude_fit["coefficients"]["wind_magnitude_mps"] * x_line
    ax.plot(
        x_line,
        y_line,
        color=COLORS["orange"],
        linewidth=2.2,
        label="Magnitude-only trend",
        zorder=2,
    )
    ax.scatter(
        combo_df["wind_magnitude_mps"],
        fit["predicted"],
        marker="x",
        s=90,
        linewidth=2.0,
        color=COLORS["red"],
        label="Component + interaction prediction",
        zorder=4,
    )
    ax.set_ylabel("Square RMS true-path deviation (m)")
    ax.set_title("Wind components explain most accepted-cell tracking degradation", loc="left", fontweight="bold")
    ax.text(
        0.02,
        0.94,
        f"Component+interaction R2 = {fit['r2']:.3f}; residual RMSE = {fit['rmse_m']:.2f} m",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        bbox={"facecolor": "white", "edgecolor": "#DDDDDD", "pad": 4},
    )
    ax.legend(frameon=False, loc="lower right")
    cbar = fig.colorbar(sc, ax=ax, shrink=0.9)
    cbar.set_label("East wind component (m/s)")
    style_axes(ax)

    axr.axhline(0, color="#222222", linewidth=1)
    axr.scatter(
        combo_df["wind_magnitude_mps"],
        fit["residual"],
        c=combo_df["y_wind_mps"],
        cmap="plasma",
        edgecolor="#222222",
        linewidth=0.6,
        s=70,
        zorder=3,
    )
    axr.set_xlabel("Wind magnitude (m/s)")
    axr.set_ylabel("Residual (m)")
    style_axes(axr)
    for ext in ("png", "svg"):
        fig.savefig(PLOTS / f"rms_vs_wind_component_model.{ext}", dpi=220)
    plt.close(fig)


def replicate_plot(run_df: pd.DataFrame, combo_df: pd.DataFrame):
    combo_df = combo_df.sort_values(["wind_magnitude_mps", "x_wind_mps", "y_wind_mps"]).reset_index(drop=True)
    positions = {combo: i for i, combo in enumerate(combo_df["combo_key"])}
    fig, ax = plt.subplots(figsize=(11.5, 6.8), constrained_layout=True)
    for _, row in combo_df.iterrows():
        x = positions[row["combo_key"]]
        ax.errorbar(
            x,
            row["square_rms_true_path_dev_mean_m"],
            yerr=0 if pd.isna(row["square_rms_true_path_dev_std_m"]) else row["square_rms_true_path_dev_std_m"],
            fmt="o",
            color=COLORS["blue"],
            ecolor=COLORS["gray"],
            capsize=4,
            markersize=7,
            zorder=3,
        )
    for _, row in run_df.iterrows():
        x = positions[row["combo_key"]]
        jitter = (int(row["run_alias"].split("_")[-1]) - 2) * 0.08 if isinstance(row["run_alias"], str) else 0
        ax.scatter(
            x + jitter,
            row["square_rms_true_path_dev_m"],
            s=28,
            color=COLORS["orange"],
            edgecolor="#222222",
            linewidth=0.4,
            zorder=4,
        )
    ax.set_xticks(range(len(combo_df)), combo_df["combo_key"], rotation=45, ha="right")
    ax.set_ylabel("Square RMS true-path deviation (m)")
    ax.set_title("Replicate spread is small for most cells; edge-adjacent cells show the largest instability", loc="left", fontweight="bold")
    ax.legend(
        [
            plt.Line2D([0], [0], marker="o", color=COLORS["blue"], linestyle="", markersize=7),
            plt.Line2D([0], [0], marker="o", color=COLORS["orange"], linestyle="", markersize=6),
        ],
        ["Combo mean +/- replicate std", "Accepted run"],
        frameon=False,
        loc="upper left",
    )
    style_axes(ax)
    for ext in ("png", "svg"):
        fig.savefig(PLOTS / f"replicate_variability_square_rms.{ext}", dpi=220)
    plt.close(fig)


def loiter_scatter(combo_df: pd.DataFrame):
    fit = model_fit(combo_df, ["square_rms_true_path_dev_mean_m"], "loiter_after_capture_rms_mean_m")
    x = combo_df["square_rms_true_path_dev_mean_m"].to_numpy(float)
    order = np.argsort(x)
    fig, ax = plt.subplots(figsize=(8.2, 6.1), constrained_layout=True)
    sc = ax.scatter(
        x,
        combo_df["loiter_after_capture_rms_mean_m"],
        c=combo_df["wind_magnitude_mps"],
        cmap="viridis",
        edgecolor="#222222",
        linewidth=0.7,
        s=84,
        zorder=3,
    )
    ax.plot(x[order], fit["predicted"][order], color=COLORS["orange"], linewidth=2)
    ax.set_xlabel("Square RMS true-path deviation (m)")
    ax.set_ylabel("Loiter after-capture RMS radial error (m)")
    ax.set_title("Loiter is related to square tracking, but reported separately", loc="left", fontweight="bold")
    ax.text(
        0.02,
        0.94,
        "Pearson r = 0.829 (020 summary)",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        bbox={"facecolor": "white", "edgecolor": "#DDDDDD", "pad": 4},
    )
    cbar = fig.colorbar(sc, ax=ax, shrink=0.9)
    cbar.set_label("Wind magnitude (m/s)")
    style_axes(ax)
    for ext in ("png", "svg"):
        fig.savefig(PLOTS / f"loiter_vs_square_after_capture.{ext}", dpi=220)
    plt.close(fig)


def residual_plot(combo_df: pd.DataFrame, fit: dict):
    data = combo_df.copy()
    data["residual"] = fit["residual"]
    data = data.sort_values("residual")
    fig, ax = plt.subplots(figsize=(10.0, 5.8), constrained_layout=True)
    colors = [COLORS["red"] if value > 0 else COLORS["blue"] for value in data["residual"]]
    ax.bar(data["combo_key"], data["residual"], color=colors)
    ax.axhline(0, color="#222222", linewidth=1)
    ax.set_xticks(range(len(data)), data["combo_key"], rotation=45, ha="right")
    ax.set_ylabel("Observed minus model RMS (m)")
    ax.set_title("Component-model residuals expose remaining run/cell dynamics", loc="left", fontweight="bold")
    style_axes(ax)
    for ext in ("png", "svg"):
        fig.savefig(PLOTS / f"component_model_residuals.{ext}", dpi=220)
    plt.close(fig)


def write_markdown_tables(combo_df: pd.DataFrame, outcome_df: pd.DataFrame, fail_df: pd.DataFrame, metrics: dict):
    path = TABLES / "cte_tables.md"
    lines = [
        "# CTE Wind-Envelope Tables",
        "",
        "Source: corrected 020 production-like CTE report over campaign `017_params_old_009_matrix_r3_plugin_fixed`.",
        "Square metrics use SIM position over mission seq 3..22. Loiter metrics are after-capture and reported separately.",
        "",
        "## Square RMS Mean Grid",
        "",
        grid_md(combo_df, "square_rms_true_path_dev_mean_m", digits=2),
        "",
        "## Square p95 Mean Grid",
        "",
        grid_md(combo_df, "square_p95_true_path_dev_mean_m", digits=2),
        "",
        "## Accepted Combo Summary",
        "",
        "| Combo | Accepted runs | Wind magnitude m/s | RMS mean m | RMS std m | p95 mean m | p95 std m | Max mean m | Lap RMS std m | Lap slope m/lap | Corner mean m | Loiter after-capture RMS m |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in combo_df.sort_values(["wind_magnitude_mps", "x_wind_mps", "y_wind_mps"]).iterrows():
        lines.append(
            f"| `{row['combo_key']}` | {int(row['replicate_count'])} | {fmt(row['wind_magnitude_mps'])} | "
            f"{fmt(row['square_rms_true_path_dev_mean_m'])} | {fmt(row['square_rms_true_path_dev_std_m'])} | "
            f"{fmt(row['square_p95_true_path_dev_mean_m'])} | {fmt(row['square_p95_true_path_dev_std_m'])} | "
            f"{fmt(row['square_max_true_path_dev_mean_m'])} | {fmt(row['lap_rms_std_m'])} | "
            f"{fmt(row['lap_rms_slope_mean_m_per_lap'])} | {fmt(row['corner_mean_min_distance_mean_m'])} | "
            f"{fmt(row['loiter_after_capture_rms_mean_m'])} |"
        )

    lines.extend(
        [
            "",
            "## Campaign Outcome Grid",
            "",
            outcome_md(outcome_df),
            "",
            "## No-Accepted / Edge Attempts",
            "",
            "| Combo | Attempt | Status | Wind magnitude m/s | Wind / 14 m/s cruise | Duration s | Last mission evidence | Interpretation |",
            "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for _, row in fail_df[fail_df["combo_key"].isin(["wind_x_12_y_08", "wind_x_08_y_12", "wind_x_12_y_12"])].iterrows():
        lines.append(
            f"| `{row['combo_key']}` | `{row['attempt_id']}` | `{row['status']}` | "
            f"{fmt(row['wind_magnitude_mps'])} | {fmt(row['wind_to_old_cruise_ratio'])} | "
            f"{fmt(row['duration_wall_s'], 1)} | {text_or_dash(row['last_statustext'])} | {row['failure_interpretation']} |"
        )

    lines.extend(
        [
            "",
            "## Model And Repeatability Statistics",
            "",
            f"- Magnitude-only model R2: {metrics['models']['magnitude_only']['r2']:.3f}.",
            f"- East/North component model R2: {metrics['models']['component']['r2']:.3f}.",
            f"- East/North + interaction model R2: {metrics['models']['component_interaction']['r2']:.3f}.",
            f"- Accepted-adjacent RMS monotonicity: {metrics['monotonicity']['square_rms']['nondecreasing_pair_count']} / {metrics['monotonicity']['square_rms']['accepted_adjacent_pair_count']} pairs nondecreasing.",
            f"- Median within-combo RMS replicate std: {metrics['repeatability']['square_rms_std_median_m']:.2f} m.",
            f"- Maximum within-combo RMS replicate std: {metrics['repeatability']['square_rms_std_max_m']:.2f} m at `{metrics['repeatability']['square_rms_std_max_combo']}`.",
            f"- Median lap RMS std across combo means: {metrics['repeatability']['lap_rms_std_median_m']:.2f} m.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def grid_md(combo_df: pd.DataFrame, metric: str, digits=2) -> str:
    rows = ["| y \\ x | 0 | 4 | 8 | 12 |", "| --- | ---: | ---: | ---: | ---: |"]
    for y in WINDS:
        cells = []
        for x in WINDS:
            match = combo_df[(combo_df.x_wind_mps == x) & (combo_df.y_wind_mps == y)]
            if match.empty:
                cells.append("-")
            else:
                cells.append(fmt(match.iloc[0][metric], digits))
        rows.append(f"| {y} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def outcome_md(outcome_df: pd.DataFrame) -> str:
    rows = ["| y \\ x | 0 | 4 | 8 | 12 |", "| --- | --- | --- | --- | --- |"]
    short = {
        "accepted_only": "accepted",
        "partial_failure_with_accepted": "partial",
        "failure_no_accepted": "edge",
    }
    for y in WINDS:
        cells = []
        for x in WINDS:
            match = outcome_df[(outcome_df.x_wind_mps == x) & (outcome_df.y_wind_mps == y)]
            if match.empty:
                cells.append("-")
            else:
                row = match.iloc[0]
                cells.append(f"{short[row['outcome']]} ({int(row['accepted_run_count'])}/{int(row['attempt_count'])})")
        rows.append(f"| {y} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def write_conclusions(metrics: dict):
    exec_text = f"""# CTE Wind-Envelope Conclusion - Executive

The production-like CTE campaign establishes a measured operating envelope, not
just a tracking-error table. In the corrected 020 analysis of campaign `017`,
13 of 16 East/North wind cells produced accepted square/loiter data and 3
high-wind cells produced no accepted run. The calm square RMS true-path
deviation is {metrics['headline']['calm_square_rms_mean_m']:.2f} m. The worst
accepted cell, `{metrics['headline']['worst_accepted_combo']}`, is
{metrics['headline']['worst_accepted_square_rms_mean_m']:.2f} m RMS, about
{metrics['headline']['worst_to_calm_ratio']:.2f}x calm.

The degradation is explained primarily by the wind vector. A magnitude-only
model explains {metrics['models']['magnitude_only']['r2']:.3f} of combo-level
RMS variation, East/North components explain {metrics['models']['component']['r2']:.3f},
and adding the component interaction explains
{metrics['models']['component_interaction']['r2']:.3f}. That still leaves real
residual behavior, especially near the envelope edge, so this should be framed
as a measured envelope and not a perfect one-variable law.

The edge is physical. The no-accepted cells sit where the resultant wind is at
or above the production-like `AIRSPEED_CRUISE = 14 m/s`. At `wind_x_12_y_12`,
the resultant wind is 16.97 m/s, the aircraft holds roughly 14 m/s airspeed,
median groundspeed is about 2.8 m/s, and mission progress stalls at waypoint 2.
The internal EKF wind audit accepted all 38 named BIN files, so the aircraft
was seeing the advertised wind; these cells are not harness gaps.

Use this as the deck line: the production-like aircraft completes low and
moderate wind cells with quantified, predictable degradation, and then reaches
a cruise-airspeed-limited envelope edge at the high-wind corner.
"""

    tech_text = f"""# CTE Wind-Envelope Conclusion - Technical

## Scope

This package analyzes only the corrected 020 postprocessing report for campaign
`017_params_old_009_matrix_r3_plugin_fixed`, the default / production-like
parameter stack. The numeric source is the existing 020 pipeline output
generated 2026-05-14 from `build_square_postprocessing_report.py`,
`true_path_deviation.py`, and `square_loiter_mission_metrics.py`. No live
SITL/Gazebo runs and no raw BIN reprocessing were performed for this package.

Per the 020 glossary, square-path conclusions use SIM position and mission seq
3..22. Loiter is reported separately using the after-capture bounded loiter
window around seq 23. Landing is excluded from the square narrative. No CTE
values are assigned to no-accepted cells.

## Result

The campaign has {metrics['headline']['accepted_run_count']} accepted runs
across {metrics['headline']['accepted_combo_count']} accepted wind cells. Three
cells have no accepted run: `wind_x_12_y_08`, `wind_x_08_y_12`, and
`wind_x_12_y_12`. Four additional cells are partial-failure-with-accepted,
meaning at least one attempt failed but accepted evidence exists for the cell.

Calm square RMS true-path deviation is
{metrics['headline']['calm_square_rms_mean_m']:.2f} m. Worst accepted square
RMS is `{metrics['headline']['worst_accepted_combo']}` at
{metrics['headline']['worst_accepted_square_rms_mean_m']:.2f} m, with p95
{metrics['headline']['worst_accepted_square_p95_mean_m']:.2f} m. The management
tail metric should be p95, not max; max remains a stress indicator because it
is sensitive to isolated samples.

Wind-to-error behavior is strong but not total. On accepted combo means,
magnitude-only RMS fit R2 is {metrics['models']['magnitude_only']['r2']:.3f};
East/North component R2 is {metrics['models']['component']['r2']:.3f}; and
East/North plus interaction R2 is
{metrics['models']['component_interaction']['r2']:.3f}. The interaction model
has residual RMSE {metrics['models']['component_interaction']['rmse_m']:.2f} m.
Accepted-adjacent RMS steps are nondecreasing in
{metrics['monotonicity']['square_rms']['nondecreasing_pair_count']} of
{metrics['monotonicity']['square_rms']['accepted_adjacent_pair_count']} pairs.
That supports a degradation-with-wind conclusion while preserving the observed
route-phase and run-to-run structure.

Repeatability is credible for the accepted cells. Median within-combo RMS
replicate standard deviation is
{metrics['repeatability']['square_rms_std_median_m']:.2f} m. The largest
within-combo RMS spread is
{metrics['repeatability']['square_rms_std_max_m']:.2f} m at
`{metrics['repeatability']['square_rms_std_max_combo']}`, an edge-adjacent
cell. Median lap RMS standard deviation across combo means is
{metrics['repeatability']['lap_rms_std_median_m']:.2f} m, and the median lap
slope is {metrics['repeatability']['lap_rms_slope_median_m_per_lap']:.2f}
m/lap, indicating repeated exposure is mostly stable with some edge-adjacent
recovery dynamics.

Loiter after capture is related but not interchangeable with square tracking.
The 020 summary reports Pearson r =
{metrics['headline']['square_vs_loiter_after_capture_r_pearson']:.3f} between
square RMS and loiter-after-capture RMS. This package therefore shows the
relationship visually, but does not use loiter as a proxy for square CTE.

## Envelope Mechanism

The no-accepted cells are clustered where resultant wind approaches or exceeds
the production-like cruise airspeed. `wind_x_12_y_08` and `wind_x_08_y_12` have
14.42 m/s resultant wind, slightly above the 14 m/s cruise setting. The high
corner, `wind_x_12_y_12`, has 16.97 m/s resultant wind. The source failure
analysis records approximately 14 m/s median airspeed, about 2.8 m/s median
groundspeed, and mission progress stalled at `Mission: 2 WP` for that cell.

The internal EKF wind audit accepted all 38 named BIN files in campaign `017`.
That means filename wind intent matched BIN-internal wind within the audit
tolerance; the edge cells are aerodynamic/energy-limit outcomes under valid
wind injection.

## Limitations

This is SITL + Gazebo simulation evidence, not hardware flight evidence. The
headline applies only to the default / production-like parameter stack. Campaign
`018_New_Param_Full_CTE_Matrix` used an expanded-authority, more aggressive
configuration that was later abandoned as unrealistic; its numbers are not used
as the production-like tracking headline. Mission edge and heading are
confounded in the square route, so directional plots must be described as
mission edge/heading effects, not pure aerodynamic heading effects.
"""

    (OUT / "written_conclusion_exec.md").write_text(exec_text, encoding="utf-8")
    (OUT / "written_conclusion_technical.md").write_text(tech_text, encoding="utf-8")


def write_readme(metrics: dict, files: dict):
    text = f"""# CTE Wind Envelope 017 - Curated Analysis Package

Date curated: 2026-06-02

Scope: derived analysis package for the production-like CTE wind-envelope
result. This package uses the corrected 020 report over campaign
`017_params_old_009_matrix_r3_plugin_fixed` as its numeric foundation.

## Provenance

- Dataset root, read-only reference:
  `{DATASET_ROOT}`
- Corrected 020 source report:
  `{SOURCE_ROOT}`
- 020 generated UTC: `{metrics['provenance']['source_metadata']['generated_utc']}`
- 020 manifest mode: `{metrics['provenance']['source_metadata']['manifest_mode']}`
- Analysis source: SIM position only.
- Square metric basis: mission seq 3..22.
- Loiter metric basis: bounded loiter around seq 23, after-capture metrics
  preferred and reported separately.

## Script SHA256 Chain

From the 020 metadata:

| Script | SHA256 |
| --- | --- |
| `build_square_postprocessing_report.py` | `{metrics['provenance']['source_metadata']['script_sha256']['build_square_postprocessing_report.py']}` |
| `true_path_deviation.py` | `{metrics['provenance']['source_metadata']['script_sha256']['true_path_deviation.py']}` |
| `square_loiter_mission_metrics.py` | `{metrics['provenance']['source_metadata']['script_sha256']['square_loiter_mission_metrics.py']}` |

Generation script for this package lives outside evidence:

- Path: `scripts/dev/generate_cte_wind_envelope_package.py`
- SHA256: `{files['generation_script_sha256']}`

## Contents

- `cte_metrics.json` - machine-readable headline metrics, model fits,
  monotonicity, repeatability, outcome, and provenance.
- `tables/cte_tables.md` - human-readable grids and tables.
- `tables/*.csv` - selected copied source tables from the corrected 020 report.
- `plots/*.png` and `plots/*.svg` - regenerated deck-ready figures.
- `written_conclusion_exec.md` - tight executive result narrative.
- `written_conclusion_technical.md` - deeper scientific conclusion and limits.

## Raw Data Boundary

Raw BIN data and large per-run telemetry remain in the broader body of work and
were not copied here. The 017 campaign contains the raw logs and per-attempt
analysis outputs; this workspace stores only curated summaries, figures, and
traceable derived tables.

## Correctness Note

The headline result is the default / production-like parameter stack. The
`018_New_Param_Full_CTE_Matrix` campaign used an expanded-authority stack that
was later abandoned as unrealistic; it is not used here as a production-like
tracking headline.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def copy_selected_sources():
    selected = [
        "corrected_combo_summary.csv",
        "corrected_accepted_runs_summary_sim.csv",
        "corrected_campaign_outcome_summary.csv",
        "corrected_failure_envelope_attempts.csv",
    ]
    for name in selected:
        src = SOURCE_ROOT / "tables" / name
        dst = TABLES / name
        dst.write_bytes(src.read_bytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    combo_df = pd.read_csv(SOURCE_ROOT / "tables/corrected_combo_summary.csv")
    run_df = pd.read_csv(SOURCE_ROOT / "tables/corrected_accepted_runs_summary_sim.csv")
    outcome_df = pd.read_csv(SOURCE_ROOT / "tables/corrected_campaign_outcome_summary.csv")
    fail_df = pd.read_csv(SOURCE_ROOT / "tables/corrected_failure_envelope_attempts.csv")
    source_summary = read_json(SOURCE_ROOT / "scientific_summary.json")
    metadata = read_json(SOURCE_ROOT / "metadata.json")

    combo_df["xy_interaction_mps2"] = combo_df["x_wind_mps"] * combo_df["y_wind_mps"]

    magnitude_fit = model_fit(combo_df, ["wind_magnitude_mps"], "square_rms_true_path_dev_mean_m")
    component_fit = model_fit(combo_df, ["x_wind_mps", "y_wind_mps"], "square_rms_true_path_dev_mean_m")
    interaction_fit = model_fit(combo_df, ["x_wind_mps", "y_wind_mps", "xy_interaction_mps2"], "square_rms_true_path_dev_mean_m")

    worst = combo_df.sort_values("square_rms_true_path_dev_mean_m", ascending=False).iloc[0]
    std_series = combo_df["square_rms_true_path_dev_std_m"].dropna()
    std_max_idx = combo_df["square_rms_true_path_dev_std_m"].idxmax()
    lap_std_series = combo_df["lap_rms_std_m"].dropna()
    lap_slope_series = combo_df["lap_rms_slope_mean_m_per_lap"].dropna()

    no_accepted = outcome_df[outcome_df["outcome"] == "failure_no_accepted"].copy()
    no_accepted["wind_to_cruise_ratio"] = no_accepted["wind_magnitude_mps"] / CRUISE_MPS

    metrics = {
        "date_curated": "2026-06-02",
        "headline": {
            "campaign": "017_params_old_009_matrix_r3_plugin_fixed",
            "corrected_report": "020_Old_Param_Fixed_CTE_Report/summary/corrected",
            "accepted_run_count": int(source_summary["dataset_run_count"]),
            "accepted_combo_count": int(source_summary["combo_count"]),
            "no_accepted_combo_count": int((outcome_df["outcome"] == "failure_no_accepted").sum()),
            "partial_failure_with_accepted_combo_count": int((outcome_df["outcome"] == "partial_failure_with_accepted").sum()),
            "calm_square_rms_mean_m": float(source_summary["calm_square_rms_mean_m"]),
            "worst_accepted_combo": str(worst["combo_key"]),
            "worst_accepted_square_rms_mean_m": float(worst["square_rms_true_path_dev_mean_m"]),
            "worst_accepted_square_p95_mean_m": float(worst["square_p95_true_path_dev_mean_m"]),
            "worst_to_calm_ratio": float(worst["square_rms_true_path_dev_mean_m"] / source_summary["calm_square_rms_mean_m"]),
            "square_vs_loiter_after_capture_r_pearson": float(source_summary["square_vs_loiter_after_capture_r_pearson"]),
            "ekf_internal_wind_audit_named_bins_accepted": 38,
            "ekf_internal_wind_audit_named_bins_rejected": 0,
        },
        "models": {
            "magnitude_only": {k: v for k, v in magnitude_fit.items() if k not in {"predicted", "residual"}},
            "component": {k: v for k, v in component_fit.items() if k not in {"predicted", "residual"}},
            "component_interaction": {k: v for k, v in interaction_fit.items() if k not in {"predicted", "residual"}},
        },
        "monotonicity": {
            "square_rms": adjacent_monotonicity(combo_df, "square_rms_true_path_dev_mean_m"),
            "square_p95": adjacent_monotonicity(combo_df, "square_p95_true_path_dev_mean_m"),
        },
        "repeatability": {
            "square_rms_std_median_m": float(std_series.median()),
            "square_rms_std_mean_m": float(std_series.mean()),
            "square_rms_std_max_m": float(combo_df.loc[std_max_idx, "square_rms_true_path_dev_std_m"]),
            "square_rms_std_max_combo": str(combo_df.loc[std_max_idx, "combo_key"]),
            "lap_rms_std_median_m": float(lap_std_series.median()),
            "lap_rms_std_mean_m": float(lap_std_series.mean()),
            "lap_rms_slope_median_m_per_lap": float(lap_slope_series.median()),
            "lap_rms_slope_mean_m_per_lap": float(lap_slope_series.mean()),
        },
        "no_accepted_cells": [
            {
                "combo_key": str(row["combo_key"]),
                "x_wind_mps": float(row["x_wind_mps"]),
                "y_wind_mps": float(row["y_wind_mps"]),
                "wind_magnitude_mps": float(row["wind_magnitude_mps"]),
                "wind_to_cruise_ratio": float(row["wind_to_cruise_ratio"]),
                "attempt_count": int(row["attempt_count"]),
                "accepted_run_count": int(row["accepted_run_count"]),
                "outcome": row["outcome"],
            }
            for _, row in no_accepted.sort_values(["y_wind_mps", "x_wind_mps"]).iterrows()
        ],
        "physical_edge_examples_from_failure_analysis": [
            {
                "combo_key": "wind_x_12_y_08",
                "resultant_wind_mps": 14.42,
                "airspeed_target_mps": 14.0,
                "groundspeed_p50_mps": 0.1,
                "groundspeed_p95_mps": 0.1,
                "last_mission_evidence": "Mission: 2 WP; Mission: 3 WP; Reached waypoint #3 dist 19m; Mission: 4 WP",
            },
            {
                "combo_key": "wind_x_08_y_12",
                "resultant_wind_mps": 14.42,
                "airspeed_target_mps": 14.0,
                "groundspeed_p50_mps": 0.1,
                "groundspeed_p95_mps": 0.2,
                "last_mission_evidence": "Reached waypoint #3 dist 21m; Mission: 4 WP; Reached waypoint #4 dist 0m; Mission: 5 WP",
            },
            {
                "combo_key": "wind_x_12_y_12",
                "resultant_wind_mps": 16.97,
                "airspeed_target_mps": 14.0,
                "actual_airspeed_p50_mps": 14.0,
                "groundspeed_p50_mps": 2.8,
                "groundspeed_p95_mps": 3.5,
                "duration_wall_s": 4536.9,
                "last_mission_evidence": "Mission: 1 Takeoff; Takeoff complete at 100.18m; Mission: 2 WP",
            },
        ],
        "accepted_combo_metrics": [
            {key: finite_or_none(value) for key, value in row.items()}
            for row in combo_df.drop(columns=["xy_interaction_mps2"]).to_dict(orient="records")
        ],
        "source_tables": {
            "combo_summary": "tables/corrected_combo_summary.csv",
            "accepted_runs_sim": "tables/corrected_accepted_runs_summary_sim.csv",
            "campaign_outcome": "tables/corrected_campaign_outcome_summary.csv",
            "failure_envelope_attempts": "tables/corrected_failure_envelope_attempts.csv",
            "human_tables": "tables/cte_tables.md",
        },
        "plot_inventory": {
            "campaign_outcome_envelope_heatmap": "plots/campaign_outcome_envelope_heatmap.png",
            "square_rms_heatmap": "plots/square_rms_heatmap.png",
            "square_p95_heatmap": "plots/square_p95_heatmap.png",
            "rms_vs_wind_component_model": "plots/rms_vs_wind_component_model.png",
            "replicate_variability_square_rms": "plots/replicate_variability_square_rms.png",
            "loiter_vs_square_after_capture": "plots/loiter_vs_square_after_capture.png",
            "component_model_residuals": "plots/component_model_residuals.png",
        },
        "provenance": {
            "dataset_root": str(DATASET_ROOT),
            "corrected_report_root": str(SOURCE_ROOT),
            "source_metadata": metadata,
            "input_file_sha256": {
                "scientific_summary.json": sha256(SOURCE_ROOT / "scientific_summary.json"),
                "metadata.json": sha256(SOURCE_ROOT / "metadata.json"),
                "corrected_combo_summary.csv": sha256(SOURCE_ROOT / "tables/corrected_combo_summary.csv"),
                "corrected_accepted_runs_summary_sim.csv": sha256(SOURCE_ROOT / "tables/corrected_accepted_runs_summary_sim.csv"),
                "corrected_campaign_outcome_summary.csv": sha256(SOURCE_ROOT / "tables/corrected_campaign_outcome_summary.csv"),
                "corrected_failure_envelope_attempts.csv": sha256(SOURCE_ROOT / "tables/corrected_failure_envelope_attempts.csv"),
            },
            "raw_bin_boundary": "Raw BIN and large per-run telemetry remain in the old workspace reference path and were not copied into this curated package.",
            "old_workspace_modified": False,
        },
    }

    generation_script_sha = sha256(Path(__file__))
    metrics["provenance"]["generation_script"] = {
        "path": "scripts/dev/generate_cte_wind_envelope_package.py",
        "sha256": generation_script_sha,
    }

    copy_selected_sources()
    heatmap(
        grid_from(combo_df, "square_rms_true_path_dev_mean_m"),
        "Square RMS true-path deviation - accepted cells",
        "RMS deviation (m)",
        "square_rms_heatmap",
        cmap="viridis",
    )
    heatmap(
        grid_from(combo_df, "square_p95_true_path_dev_mean_m"),
        "Square p95 true-path deviation - accepted cells",
        "p95 deviation (m)",
        "square_p95_heatmap",
        cmap="magma",
    )
    outcome_heatmap(outcome_df)
    trend_plot(combo_df, interaction_fit, magnitude_fit)
    residual_plot(combo_df, interaction_fit)
    replicate_plot(run_df, combo_df)
    loiter_scatter(combo_df)

    (OUT / "cte_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown_tables(combo_df, outcome_df, fail_df, metrics)
    write_conclusions(metrics)
    files = {"generation_script_sha256": generation_script_sha}
    write_readme(metrics, files)


if __name__ == "__main__":
    main()
