# ADR-0013: Airspeed Envelope Overlay Mechanism

Status: Proposed

Date: 2026-06-14

Implements the mechanism for the Envelope Sensitivity Matrix in ADR-0012.

## Context

ADR-0012 requires varying `AIRSPEED_CRUISE` / `AIRSPEED_MAX` across campaigns
while keeping the fault-injection experiment byte-for-byte identical. The
codebase already separates these two concerns; this ADR records that the matrix
is implemented by exercising the existing seam, not by adding a new one.

Traced facts (current code):

- The envelope lives only in the airspeed overlay file
  (`config/overlays/plane_airspeed.parm`: `AIRSPEED_CRUISE 14`,
  `AIRSPEED_MIN 10`, `AIRSPEED_MAX 22`). It is not a `SIM_ARSPD_*` parameter.
- Overlays are loaded once at SITL boot:
  `AirspeedFailureConfig.param_file_stack` -> `effective_param_stack`
  (`config.py`) -> `launch_sitl(..., param_files=param_stack)`
  (`environment.py`). The envelope is fixed for the whole campaign.
- The case generator (`case_generator.py`) only ever emits `SIM_ARSPD_*`
  payloads. It has no concept of cruise/max and must not gain one.
- The CLI already accepts a swappable airspeed overlay via `--param-airspeed`,
  resolved through `resolve_param_files(param_base, param_airspeed, ...)` and
  wired into `param_file_stack` in `cli/run.py`.

## Decision

Implement the matrix as **new overlay files driven through the existing
`--param-airspeed` seam**. Zero edits to the fault-injection core.

### Add

- Four overlay files in `config/overlays/`, each a copy of
  `plane_airspeed.parm` differing only in the envelope block. Naming follows the
  precedent already documented in `plane_airspeed.parm`
  (named overlays such as `plane_airspeed_cte_high_wind_aggressive.parm`):
  - `plane_airspeed_cruise17.parm`     -> `AIRSPEED_CRUISE 17`, `MAX 22`
  - `plane_airspeed_max18.parm`        -> `AIRSPEED_CRUISE 14`, `MAX 18`
  - `plane_airspeed_max28.parm`        -> `AIRSPEED_CRUISE 14`, `MAX 28`
  - `plane_airspeed_scaled18_28.parm`  -> `AIRSPEED_CRUISE 18`, `MAX 28`

  Every other line (the `ARSPD_*`, `SIM_WIND_*`, `AHRS_WIND_MAX`, comments)
  stays identical to `plane_airspeed.parm` so the envelope is the only changed
  variable. `AIRSPEED_MIN` stays 10 in all four.

- One thin matrix driver that invokes the existing runner once per overlay into
  a per-cell campaign root. For v1, five explicit runner invocations are
  preferred over a loop, because they are individually auditable and produce
  independent campaign roots and manifests.

### Unchanged (frozen)

`case_generator.py`, the ramp/pulse injection schedules, the
`SIM_ARSPD_RATIO = ARSPD_RATIO / k^2` recipe, the suite runner core
(scheduler / manifest / attempt loop), and the behavior classifier in
`analyzers.py`. The baseline `14/22` cell reuses the already-accepted Phase 4A
evidence and is not re-flown.

### Run shape (per cell)

```
run ... --param-airspeed config/overlays/plane_airspeed_max18.parm \
        --case ratio_bias_ramp_p10_to_p200_headwind \
        --runs-per-... 3 --campaign-root var/runs/envelope_matrix/max18
```

Boot applies the envelope; the inner experiment injects the fault unchanged;
per-cell metrics are emitted; the driver advances to the next overlay.

## Alternatives considered

- **A new `envelope` field on the plugin config / case model.** Rejected: it
  duplicates state that already lives authoritatively in the parm overlay and
  would let the case generator become envelope-aware, violating the genericity
  the second-plugin (GPS) work established.
- **Mutating `AIRSPEED_*` in flight via MAVLink.** Rejected: the envelope is a
  vehicle configuration, not a stimulus; mid-flight mutation would conflate the
  config change with the fault and break per-attempt provenance.

## Consequences

- The only reviewable diff for the matrix is four small `.parm` files plus a
  driver and the ADR family. This is a genericity proof: config-as-input, not
  code-as-config.
- Each cell yields an independent campaign root, manifest, and per-attempt
  `run_config.json` recording the exact overlay file and its hash, preserving
  provenance per the existing reset/readback protocol (ADR-0008).
- An optional later refinement is a single matrix-runner module, but it is not
  required for v1 and is out of scope here.
