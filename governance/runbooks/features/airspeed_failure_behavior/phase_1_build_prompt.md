# Phase 1 Build Prompt — Airspeed Failure Behavior Plugin (No-SITL Foundation)

This file is the handoff brief for the coding agent that will implement Phase 1.
It is a prompt, not a spec change. The authoritative design is the accepted ADRs
(`governance/decisions/ADR-0006..0011`) and the runbook bundle in this directory.
If anything here conflicts with those, the ADRs win — stop and flag it.

---

## Your task

Implement **Phase 1 only** of the airspeed failure behavior lane: the **no-SITL
plugin foundation**. Do NOT run SITL or Gazebo. Do NOT make any live-evidence
claim. Do NOT start Phase 2 (smoke) or Phase 3 (campaign). Do NOT edit
`src/sim_ard_gaw/campaigns/test_suite/core/` — the whole point of this feature is
to prove a second plugin needs zero framework-core edits. If you think you need a
core edit, stop and report why instead of doing it.

You are working in `/home/ahmed/ardupilot_workspace_next`. Read `AGENTS.md`,
`.ai/entrypoint.md`, `.ai/current.md`, `governance/standards/change_control.md`,
and `governance/standards/naming.md` before writing files. Use `rg` for
searches.

## Required reading before you write code

1. The accepted decisions (terse):
   `governance/decisions/ADR-0006-airspeed-failure-mission-design.md` through
   `ADR-0011-airspeed-failure-behavior-classification.md`.
2. The full reasoning, payload tables, equations, and open validation items:
   `governance/runbooks/features/airspeed_failure_behavior/design_research.md`
   and `design_adrs.md`.
3. The runbook contract:
   `governance/runbooks/features/airspeed_failure_behavior/plan.md`,
   `implementation.md`, `review.md`, `evidence.md`.
4. The existing sibling plugin you will mirror (do not import its internals as a
   dependency, but copy its structure and conventions):
   `src/sim_ard_gaw/campaigns/test_suite/plugins/wind_matrix/` —
   especially `plugin.py`, `config.py`, `defaults.py`, `case_generator.py`,
   `analyzers.py`, `manifest.py`.
5. The framework interfaces you must satisfy (read, do not edit):
   `src/sim_ard_gaw/campaigns/test_suite/core/case_generator.py` (the
   `CaseGenerator` ABC with `iter_cases()`), `core/models.py` (`TestCase`,
   `AttemptContext`, `AttemptRecord`, `Verdict`, etc.), and the registry
   `src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py`.

## Hard design facts you must encode (do not re-derive from case names)

These come from local ArduPilot source review (see `design_research.md`); the
`011_Sensor_Failure_Injection` JSON is partly WRONG on these and must not be
trusted over source:

- Default stack uses `ARSPD_TYPE 100` -> `AP_Airspeed_SITL` backend.
- `SIM_ARSPD_FAIL` is a forced airspeed VALUE in m/s, not a boolean.
  `fail_primary` requests `1` (=> airspeed reads ~1 m/s, stuck low). Single case,
  no variations.
- `SIM_ARSPD_OFS` has NO effect on `TYPE 100`. It is used by NO active case. Keep
  it only in the parameter-probe name-existence list.
- `SIM_ARSPD_PITOT` only acts when `SIM_ARSPD_FAILP != 0`. `pitot_500pa` uses
  `SIM_ARSPD_FAILP=500` (NOT `SIM_ARSPD_PITOT`).
- `SIM_ARSPD_RND` is Pa noise, source default `2.0`. `noise_5`/`noise_10` set 5/10.
- `SIM_ARSPD_SIGN=1` flips differential-pressure sign (airspeed collapses ~0).
- `SIM_ARSPD_RATIO` biases reported airspeed ONLY via mismatch with the
  vehicle-side `ARSPD_RATIO`. The relation is:
  `reported = true * sqrt(ARSPD_RATIO / SIM_ARSPD_RATIO)`. For a target bias
  factor `k = 1 + bias_percent/100`, inject `SIM_ARSPD_RATIO = ARSPD_RATIO / k^2`.
- Reset restores SOURCE DEFAULTS, not zeros:
  `RND=2.0, OFS=2013, FAIL=0, FAILP=0, PITOT=0, SIGN=0, RATIO=1.99`.
  (`RATIO=0` would break the model.)

## Cases the generator must produce

Fixed cases:

```text
healthy_reference   # assert source defaults; inject nothing
noise_5             # SIM_ARSPD_RND=5
noise_10            # SIM_ARSPD_RND=10
pitot_500pa         # SIM_ARSPD_FAILP=500
fail_primary        # SIM_ARSPD_FAIL=1
sign_reversed       # SIM_ARSPD_SIGN=1
```

Ratio sweep — a RECIPE, not a hand list. The generator takes a list of signed
`bias_percent` values and emits one case each:

- name `ratio_bias_pNN` (reads high, +NN%) / `ratio_bias_mNN` (reads low, -NN%).
- payload computed as `SIM_ARSPD_RATIO = vehicle_arspd_ratio / k^2`,
  `k = 1 + bias_percent/100`.
- In Phase 1 (no SITL) the vehicle `ARSPD_RATIO` is not yet measured. Carry the
  cases with a `calibration_required: true` flag and store `bias_percent`, `k`,
  and the formula; compute the concrete `SIM_ARSPD_RATIO` lazily from a supplied
  `vehicle_arspd_ratio` (default to the source value 2 for dry-run/list, but mark
  it unverified). Do NOT bake a hard-coded `SIM_ARSPD_RATIO` number as if locked.
- Generator MUST clamp/refuse `bias_percent` beyond a configured low-side floor
  (default `-70`); below that the flight is the `fail_primary`/`sign_reversed`
  regime, not a ratio case. This guard must be explicit and tested.

v1 thin slice (the default case list for v1):
`healthy_reference, noise_5, noise_10, pitot_500pa, fail_primary, sign_reversed,
ratio_bias_p10, ratio_bias_p30, ratio_bias_p50, ratio_bias_m10, ratio_bias_m30,
ratio_bias_m50`. The full `+10..+100 / -10..-50` sweep must be reachable by
passing a longer `bias_percent` list — no code change.

## Default stack (do not change config values)

| Item | Value |
| --- | --- |
| Mission | `assets/missions/airspeed_failure_behavior_mission.waypoints` |
| SITL target | `plane-cte` |
| Gazebo target | `gazebo-plane-cte` |
| Base params | `config/vehicles/plane_base.parm` |
| Airspeed overlay | `config/overlays/plane_airspeed.parm` |
| Reference wind | Gazebo ENU `x=-5, y=0, z=0` m/s |
| Injection trigger | first `MISSION_CURRENT seq==4` edge after front-half progress |

## Where the code goes (mirror wind_matrix)

Plugin package:
`src/sim_ard_gaw/campaigns/test_suite/plugins/airspeed_failure/` with modules per
`implementation.md` (`config.py`, `defaults.py`, `case_generator.py`,
`environment.py`, `stimulus.py`, `control.py`, `monitor.py`, `analyzers.py`,
`manifest.py`, `plugin.py`, and a public `build_plugin(config)` + `__init__.py`).

CLI: `src/sim_ard_gaw/campaigns/test_suite/cli/run_airspeed_failure.py`.

Registry: add key `airspeed_failure` to
`src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py` following the exact
`_wind_matrix_factory` pattern (lazy import inside the factory; construct from a
typed `AirspeedFailureConfig`). This is the ONLY edit outside the new plugin
package and the new CLI file — and it is an additive dict entry, not a core-logic
change.

Runtime output root (Phase 2+, not this phase):
`var/runs/airspeed_failure_behavior_<timestamp>/`. Do not write runtime output or
plugin code into `evidence/`.

## CLI surface (Phase 1, no SITL)

Must work without starting SITL/Gazebo:

```bash
python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --list-cases
python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --dry-run --case healthy_reference
python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --dry-run --case fail_primary
python3 -m sim_ard_gaw.campaigns.test_suite.cli.run_airspeed_failure --dry-run --case ratio_bias_p30
```

`--list-cases` prints the case ids (with the v1 slice by default and an option to
expand the ratio sweep). `--dry-run --case X` validates the case, prints the
exact injection payload + reset payload + trigger metadata + readback rule, and
constructs the plugin WITHOUT launching anything. Provide a parameter-probe /
schema-validation path that checks the required `SIM_ARSPD_*` names (it may be a
pure-validation stub in Phase 1; the live probe runs in Phase 2).

Also expose case metadata each case must carry: exact (or recipe-computed)
`SIM_ARSPD_*` injection payload, reset payload (source defaults), units +
semantic note per param, readback rule + tolerance (exact for enum/integer-valued
`FAIL`/`SIGN`, `1e-3` for floats), trigger point metadata (entering seq 4), and
acceptance/observation-quality requirements.

## Required no-SITL tests (under `tests/unit/`, name `test_airspeed_failure_*.py`)

Mirror the wind_matrix test style (`tests/unit/test_wind_matrix_*.py`). Cover:

- Case generation for the fixed cases.
- Ratio-sweep recipe: correct `SIM_ARSPD_RATIO = ARSPD_RATIO/k^2` for several
  `bias_percent` values and a chosen `vehicle_arspd_ratio`; correct `pNN/mNN`
  naming; deterministic order.
- Low-side floor clamp/refusal guard.
- Invalid case id rejection before launch.
- `SIM_ARSPD_*` parameter schema validation (required names present).
- Exact injection payload AND reset payload serialization (reset == source
  defaults, never zeros; `fail_primary`=1; `pitot_500pa` uses `FAILP`).
- Encoded semantics guards: a test asserting `OFS` is in no active case payload,
  and `pitot_500pa` does not rely on `SIM_ARSPD_PITOT` alone.
- Injection-trigger metadata = entering seq 4 (first `MISSION_CURRENT seq==4`
  edge), and the parameter-readback success/failure handling shape.
- Fixed-wind artifact schema (`reference_wind.json` fields per ADR-0010).
- Airspeed analysis artifact schema (`airspeed_behavior_summary.json`,
  `airspeed_signal_metrics`, `mission_progress.json` incl. AUTO->RTL transition
  seq, `mode_timeline`, `altitude_speed_envelope.json`, optional
  `tecs_response.json`).
- Behavior-class classification logic (the four classes) and the planned-RTL vs
  fault-RTL discriminator (max mission seq at AUTO->RTL transition).
- Observation-quality classification + accepted-observation gating (a bad flight
  counts only if injection succeeded, wind verified, window met, artifacts
  present; failed launch / failed readback / pre-injection / incomplete do NOT
  count).
- Manifest accepted-count logic counts valid observations, not only good flights.
- Plugin construction with NO SITL and with the legacy wind runner NOT imported
  (assert the airspeed plugin does not import `run_one`/`run_matrix`/
  `run_matrix_round_robin`).
- CLI `--list-cases` and `--dry-run`.

## Things that are explicitly NOT Phase 1 (leave as stubs / interfaces only)

- No live SITL/Gazebo launch, no real MAVLink connection, no real `gz topic`
  publish. The `environment`/`control`/`monitor`/`stimulus` modules define the
  interfaces and artifact shapes; their live bodies are exercised in Phase 2.
- Do not lock the ratio `SIM_ARSPD_RATIO` numbers (needs measured vehicle ratio).
- Do not set the calibrated classification thresholds (needs healthy_reference
  smoke); only the coarse provisional gates from ADR-0011
  (`MIN_POST_INJECTION_S=20`, `ALT_LOSS_MAX_M=30`) are placed as flagged defaults.

## Reuse vs duplicate

Reuse framework-owned helpers from `core/` by IMPORT (case generator ABC, models,
analyzer chain, attempt runner, manifest base) — do not copy them. For wind
publish/echo and MAVLink mission-progress patterns, you MAY study
`plugins/wind_matrix/wind_injection.py` and `mavlink_control.py` and write the
airspeed plugin's own equivalents; do not import the wind plugin's modules as a
dependency (that would couple the two lanes). The airspeed analyzers must be the
primary scorer — do NOT reuse CTE/square analyzers as the scorer (CTE is optional
supporting context only).

## Done criteria for Phase 1

- Plugin constructs with no SITL; `--list-cases` and `--dry-run` work.
- Registry resolves `airspeed_failure`.
- All no-SITL tests above pass: `pytest tests/unit/test_airspeed_failure_*.py`.
- No edit to `core/`. The only non-plugin edit is the additive registry key.
- No legacy wind-runner import needed for construction.
- Run `make doctor` (you touched governance/runbook/index files only if you
  update status; if you only add code+tests, run the targeted pytest and note
  whether `make doctor` was needed).
- Update `review.md` Phase 1 gate status and `.ai/current.md` active-work pointer
  to reflect Phase 1 progress. Do NOT claim Phase 2/3/4 or any live evidence.
- Follow `governance/standards/git_commit_style.md` for any commit; do not push
  without explicit authorization; keep the commit scoped to the new plugin + CLI
  + registry key + tests (+ status pointers), leaving unrelated working-tree
  changes alone.

## If you get blocked

If a required `SIM_ARSPD_*` name, a core interface, or a framework assumption does
not match what this prompt says, STOP and report the mismatch with the exact file
and line rather than guessing or editing core. The design owner would rather
re-decide than have the foundation drift.
