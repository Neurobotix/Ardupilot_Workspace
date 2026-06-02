# Pillar A Flight Results Rollup

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
- SHA256: `a79900dbdb075c3707a1d6a6de35bcf378ee601ca232298049cb50b822d93a60`
