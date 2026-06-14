# Airspeed Failure Behavior — Curated Interim Analysis Package (2026-06-11)

Curated, reviewed analysis artifacts for the `airspeed_failure` behavior lane.
This package supports the interim report
`evidence/reports/features/2026-06-11_airspeed_failure_behavior_interim_analysis.md`.
It was promoted as an **interim characterization package** and remains not a
full-lane claim or safety certification. On 2026-06-14 it was accepted for the
bounded Phase 4A ratio/ramp/pulse characterization scope by
`evidence/reports/features/2026-06-14_airspeed_failure_ratio_ramp_pulse_acceptance.md`;
fixed-case repetitions and full-lane acceptance remain open.

Raw runtime output (attempt trees, `.BIN` logs, SITL state) intentionally stays
under `var/` per `governance/standards/evidence.md`. See `raw_data_index.md`
for every raw source path. `manifest.json` records the SHA-256 and `var/`
source of every curated file.

## Contents

| Directory | Experiment | Source |
| --- | --- | --- |
| `ratio_sweep/` | One-bias-per-flight signed ratio sweep, +10..+100 and −10..−50 (MAVLink-artifact metrics) | 15 run roots, 2026-06-08/09; 44 accepted attempts |
| `pulse_ladder/` | `ratio_bias_pulse_p10_to_p130_headwind` (.BIN-derived windows + ARSP U/H/Hp/TR health table) | 1 accepted attempt, 2026-06-10 |
| `ramp_p100/` | `ratio_bias_ramp_p10_to_p100_headwind` stepped ramp (.BIN-derived windows) | 1 accepted attempt, 2026-06-10 |
| `ramp_p200/` | `ratio_bias_ramp_p10_to_p200_headwind` extended ramp (.BIN-derived windows) | 1 accepted attempt, 2026-06-10 |
| `reproducibility/` | +100 ramp vs +200 ramp overlap (0..+100) window comparison incl. AOA | both ramp BINs |

## Key reviewed facts carried by this package

- The signed sweep maps a dose-response: nominal at ±10/±20, degraded from
  +30 upward with monotonically growing altitude loss; the negative side is
  asymmetric (sensor disable + monitor low-altitude aborts at −40, slow
  degraded flight at −50).
- The pulse ladder makes the airspeed health machinery visible:
  `ARSP.TR` grows with pulse size, first crosses `ARSPD_WIND_GATE=5` in the
  +60% window, after which the sensor is disabled and cyclically re-enabled
  (`pulse_ladder/pulse_window_health_summary.csv`).
- The slow stepped ramp never trips the gate (`ARSP.TR` mean ≤ ~0.48): the
  sensor stays accepted (`ARSP.U=1`, `Hp=1`) while the aircraft settles into a
  degraded equilibrium (~12.8 m/s true, ~85.6 m AGL).
- The extended +200 ramp shows raw reported airspeed rising linearly to
  ~37 m/s while the realized aircraft state stops changing after roughly
  +80..+100, consistent with controller-side clamping around
  `AIRSPEED_MAX=22` / TECS limits.
- The +100-vs-+200 overlap windows reproduce within ≲0.03 m/s and ≲0.4 m on
  all compared metrics (`reproducibility/reproducibility_metrics.json`).

## Limitations

- Single accepted attempt per within-flight experiment (pulse, both ramps);
  the +100 sweep bin has 2 accepted attempts (one pre-injection failure).
- Sweep metrics are MAVLink-derived attempt artifacts; only pulse/ramp
  packages are `.BIN`-derived.
- Results are specific to this SITL stack (ArduPlane Mini Talon Gazebo,
  `plane_base.parm` + `plane_airspeed.parm`, fixed −5 m/s ENU x wind,
  `ARSPD_WIND_MAX=0`, `ARSPD_WIND_GATE=5`, `ARSPD_OPTIONS=11`).
- The generating plugin/doc changes were uncommitted working-tree state at run
  time; each attempt's `run_config.json` under `var/` records the dirty-file
  snapshot.
