# GPS Failure Behavior — Implementation

Status: Phase 1 Chunk 3 is implemented pending review; full Phase 1 remains open.

## Implemented In Phase 1 Chunk 1

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/` | No-SITL plugin skeleton: defaults, config, deterministic case generator, stimulus metadata, manifest, analyzer schema/classifier, environment/control/monitor stubs, and plugin assembly. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | No-SITL CLI entry point for `--list-cases`, `--dry-run --case <case_id>`, and `--probe-schema`. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py` | Registry key `gps_failure`. |
| `tests/unit/test_gps_failure_phase1.py` | No-SITL unit tests for case catalog, schema, trigger metadata/helpers, dry-run JSON, registry construction, manifest counting, classifier states, and legacy-runner exclusion. |

## Implemented In Phase 1 Chunk 2

| Path | Responsibility |
| --- | --- |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/glitch.py` | Pure metre-to-degree conversion helpers for `SIM_GPS1_GLTCH_X/Y`, plus deterministic `step_glitch_payload` and `slow_drift_payload` builders. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/case_generator.py` | GLTCH cases now carry explicit frame/sign/conversion recipes, example reference-latitude payloads, and the ADR-0019 continuous slow-drift accumulation metadata case. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | Dry-run accepts `--reference-latitude-deg` and `--preview-elapsed-s` to emit preview-only resolved payloads without launching SITL. |
| `tests/unit/test_gps_failure_phase1.py` | No-SITL tests cover GLTCH unit/frame/sign behavior, dry-run preview behavior, accumulation metadata, and denial/jamming payload regressions. |

## Implemented In Phase 1 Chunk 3

| Path | Responsibility |
| --- | --- |
| `assets/missions/gps_failure_behavior_mission.waypoints` | Locked QGC WPL 110 five-item GPS mission: seq-4 injection edge, explicit 15 m/s command, approximately 36 km one-way Eastbound leg, and no reciprocal/RTL/landing items. |
| `config/overlays/plane_gps.parm` | Dedicated overlay applied after `plane_base.parm`; pins the four EKF knee inputs, complete primary EKF source set, and calm SITL wind without airspeed tuning. |
| `src/sim_ard_gaw/campaigns/test_suite/plugins/gps_failure/defaults.py` | Two-file Phase-1 default parameter stack and current overlay schema status. |
| `src/sim_ard_gaw/campaigns/test_suite/cli/run_gps_failure.py` | Dry-run output exposes the effective two-file parameter stack. |
| `tests/unit/test_gps_failure_phase1.py` | Deterministic no-SITL parsers and structural tests for mission geometry, parsed parameter values/uniqueness, stack order/override, generated case mission paths, and CLI schema output. |

## Current No-SITL Semantics

- Case generation covers `nominal`, the ADR-0019 drift-rate ladder, the
  continuous slow-drift accumulation instrument, step-glitch magnitude ladder,
  denial-duration ladder, and five jamming repeat cases.
- The trigger helpers model ADR-0020 at schema level: seq 1, 2, and 3 must be
  observed before the first seq 4; the structured helper additionally requires
  those front-half events and the seq-4 event to be armed and in `AUTO`.
- The generated acceptance requirements use the locked GPS post-injection
  observation window of at least 90 s.
- `slow_drift` and `step_glitch` recipes use the explicit contract from
  `glitch.py`: north metres convert to `SIM_GPS1_GLTCH_X` latitude degrees,
  east metres convert to `SIM_GPS1_GLTCH_Y` longitude degrees using
  `111_320 * cos(latitude_deg)`, and `SIM_GPS1_GLTCH_Z` stays a reset/default
  guard rather than a v1 fault axis.
- Dry-run without a reference latitude emits recipe metadata only. Dry-run with
  `--reference-latitude-deg` emits `resolved_payload_preview`, clearly marked as
  not the live payload.
- `slow_drift_accumulation_ramp` is a no-SITL metadata case for ADR-0019's
  continuous ramp: fresh flight, no in-flight reset, accumulation/endurance
  measurement, not independent knee points.
- The classifier keeps the seven locked behavior bands intact and uses
  `analysis_incomplete` as an analysis/quality state for short windows, missing
  artifacts, or missing mechanism/behavior fields.
- Required no-SITL artifact schema names are the locked JSON names:
  `gps_injection.json`, `gps_behavior_summary.json`,
  `ekf_innovation_metrics.json`, `truth_vs_belief.json`, `mode_timeline.json`,
  and `attitude_altitude_envelope.json`.
- The static default parameter stack is
  `config/vehicles/plane_base.parm` followed by
  `config/overlays/plane_gps.parm`; an explicit caller stack still overrides
  that default.
- The checked-in mission and overlay have static/no-SITL contract coverage.
  No live mission timing or parameter readback is implied.

## Still Open

The following are deliberately not implemented in Phase 1 no-SITL chunks:

- Trigger-time live resolution of GLTCH payloads from the actual vehicle
  latitude/time. The pure conversion and dry-run preview contract exist, but no
  MAVLink/runtime injector exists in this chunk.
- Runtime/MAVLink helpers, live SITL/Gazebo launch, mission upload/control, and
  live monitor behavior.
- EKF mechanism-gate extraction from BIN/log data.
- Full Phase 1 acceptance and any Phase 2/3/4 evidence claim.

## Live Gates (Future Phase 2)

- Read back every injected `SIM_GPS1_*` param.
- Read live `EK3_POS_I_GATE`, `EK3_GLITCH_RAD`, `FS_EKF_THRESH`, `EK3_GPS_CHECK`.
- Confirm the realized straight-leg duration and bracket the empirical knee.
