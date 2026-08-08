# ADR-0017: GPS Failure Fault Catalog And Knob Mapping

Status: Proposed

Date: 2026-07-06

The GPS failure lane injects a small catalog of real-world GPS faults with
distinct mechanisms, chosen from the SITL `SIM_GPS1_*` surface (`GPSParms` in
`src/ardupilot/libraries/SITL/SIM_GPS.cpp`), rather than sweeping every knob.

Decision:

- Four headline faults, all in v1:
  - `slow_drift` — `SIM_GPS1_GLTCH_{X,Y}` re-injected as a growing ramp (GPS
    spoofing / slow position capture).
  - `step_glitch` — `SIM_GPS1_GLTCH_{X,Y}` set to a fixed offset (multipath jump
    / sudden position pop).
  - `hard_denial` — `SIM_GPS1_ENABLE=0` (antenna/receiver loss, total denial).
  - `jamming` — `SIM_GPS1_JAM=1` (RF jamming: blackout + chaotic garbage).
- `slow_drift` and `step_glitch` share the `GLTCH` knob deliberately: `SIM_GPS.cpp`
  adds `GLTCH_{X,Y}` directly to the fix lat/lon in degrees, so the only
  difference between a ramp and a step is onset rate. This isolates onset rate as
  the single independent variable in the central knee experiment.
- All other `SIM_GPS1_*` knobs are documented-only, each excluded for a mechanism
  reason: `NUMSATS` (pre-arm gate only; does not drop `have_lock`, position stays
  truthful mid-flight), `VERR` (self-reports matching `speed_acc` → down-weighted),
  `LAG_MS` (EKF compensates lag), `ACC` (self-report only; natural first modifier
  if layering), `NOISE`/`DRFTALT` (altitude-only, baro-dominated negative
  controls). Modifier layering is future work, not this lane.

Full mechanism reasoning, alternatives, and the excluded-knob table:
`governance/runbooks/features/gps_failure_behavior/design_adrs.md`
("ADR (Proposed): GPS Fault Catalog And Knob Mapping") and `design_research.md`.

Open validation (Phase 2 smoke): confirm `SIM_GPS1_*` spellings and units live
against the SITL build before the first matrix.
