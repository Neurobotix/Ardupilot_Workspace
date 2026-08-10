# Campaign-Lane Test Coverage Gap Audit

Date: 2026-08-10
Scope: `tests/unit` and `tests/integration`, the three campaign lanes
registered in `src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py`
(`airspeed_failure`, `gps_failure`, `wind_matrix`).

This is Stage 2 of the per-lane test-naming work. Stage 1 (commit
`3f81e01`) made `test_<lane>_*` a complete glob for a campaign lane's unit
tests; that glob is what makes this audit possible to compute rather than
guess. **This audit reports only. No test was written, changed, or removed.**

## Method

A "method capability" here means something the campaign method gives every
lane — not lane physics. GPS glitch geometry is domain; a readiness report is
method. For each capability I checked three things separately, because they
disagree more often than expected:

1. Does the lane **have** the capability in production code?
2. Does the lane's **own** unit test file assert on it?
3. Is it asserted in a **cross-lane or integration** test instead?

Confusing (1) with (2) is how a coverage table becomes fiction, so absence in
column 2 is only a real gap when column 1 says the capability exists.

## Coverage table

Legend: **Y** own-lane test · **E** covered elsewhere (cross-lane/integration)
· **GAP** capability exists, untested · **N/A** capability absent, with reason.

| Capability | `airspeed_failure` | `gps_failure` | `wind_matrix` |
|---|---|---|---|
| Readiness reporting | **N/A** | **Y** `test_gps_failure_readiness.py` | **N/A** |
| Launch-target correctness | **GAP** | **Y** `test_gps_failure_launch_targets.py` | **N/A** |
| Mechanism gate | **Y** `test_airspeed_failure_mechanism_gate.py` | **Y** `test_gps_failure_mechanism_gate.py` | **N/A** |
| MAVLink contract | **GAP** | **Y** `test_gps_failure_mavlink.py`, `test_gps_failure_runtime_path.py` | **Y** `test_wind_matrix_mavlink_control.py` |
| Manifest/artifact contract | **Y** `test_airspeed_failure_campaign_contract.py` | **Y** `test_gps_failure_campaign_contract.py` | **E** |
| Case generation / sweep | **Y** | **Y** | **Y** |
| Analysis / BIN handling | **Y** (mechanism gate, real BIN) | **Y** `test_gps_failure_runtime_path.py` | **Y** `test_wind_matrix_analysis_helpers.py` |
| World / environment safety | **E** (CTE regression, see below) | **Y** (dedicated worlds) | **Y** `test_wind_matrix_world_safety.py` |

### File counts after the rename

| Lane | Files |
|---|---|
| `gps_failure` | 6 |
| `wind_matrix` | 4 |
| `airspeed_failure` | 3 |

The imbalance in the original problem statement is confirmed and is not an
artifact of naming.

## Findings, one per cell that is not plain Y

### Real gaps

**1. `airspeed_failure` — launch-target correctness. Real gap.**

The lane has the capability: `defaults.py:49-52` declares `SITL_TARGET =
"plane-cte"`, `GAZEBO_TARGET = "gazebo-plane-cte"`, and both launch commands.
No `airspeed_failure` test asserts these resolve correctly.

Partially mitigated, but not closed: `test_gps_failure_launch_targets.py`
contains `test_cte_lane_still_uses_airspeed_and_local_override` and
`test_no_gps_default_routes_through_cte`. Those are *GPS* regression guards
that happen to pin CTE behaviour — they exist to prove GPS did not disturb
the airspeed lane, and would be the wrong place to assert airspeed's own
target contract. If the GPS lane were ever retired, airspeed's launch-target
coverage would disappear with it. That coupling is the finding.

**2. `airspeed_failure` — MAVLink contract. Real gap.**

`plugins/airspeed_failure/mavlink.py` is 441 lines and includes
`upload_mission`, `verify_mission`, `arm_vehicle`, `set_auto_mode`,
`read_param`, and `wait_for_vehicle_ready` — the same surface both other
lanes test with fake connections. Zero airspeed test files mention MAVLink
at all (verified by grep across all three airspeed files).

Both other lanes demonstrate this is testable without SITL:
`test_gps_failure_mavlink.py` uses `_FakeParamConnection`, and
`test_wind_matrix_mavlink_control.py` uses `_FakeMaster` with scripted
message streams. So this is a genuine hole with a proven pattern available,
not a domain difference.

This is the highest-value gap in the table: it is the largest untested
production surface, and it is arming and mission-upload code.

### Covered elsewhere

**3. `wind_matrix` — manifest/artifact contract. Covered elsewhere.**

No `test_wind_matrix_*` file asserts on the manifest. It is covered by
`test_test_suite_manifest_generic_view.py` (whose only lane is `wind_matrix`),
`test_campaign_manifest_safety.py`, and the integration flow
`tests/integration/test_phase5_wrapper_manifest_flow.py` (also `wind_matrix`).
wind_matrix is in fact the lane those generic tests are written *against*.
Not a gap; worth knowing that the coverage lives outside the lane glob, so a
naive per-lane conformance check would report a false positive here.

**4. `airspeed_failure` — world/environment safety. Covered elsewhere.**

Covered indirectly via the CTE assertions in the GPS launch-target file, with
the same fragile cross-lane coupling described in finding 1.

### Not applicable

**5. Readiness reporting — `airspeed_failure`, `wind_matrix`. N/A as built,
but this is the weakest N/A in the table.**

`readiness.py` exists only under `plugins/gps_failure/`, and `--preflight`
exists only in `cli/run_gps_failure.py`. The capability genuinely does not
exist for the other two lanes, so there is nothing to test and no test should
be written.

Recorded as a **method gap rather than a test gap**: the readiness report was
built for GPS because GPS gated a protected live action behind Phase A-H
proof. Nothing about it is GPS-specific — it reports scheduled cases, the
manifest/artifact contract, the parameter stack, and gate status. Whether the
other lanes should have one is a design decision for Ahmed, not something to
resolve by adding tests.

**6. Mechanism gate — `wind_matrix`. N/A, correctly.**

`mechanism_gate.py` exists for `airspeed_failure` and `gps_failure` only. A
mechanism gate proves an injected fault actually reached the vehicle's
estimator. `wind_matrix` sweeps an environmental condition rather than
injecting a sensor fault into a signal path, so there is no mechanism to
gate. This is a true domain difference — the one place where uneven coverage
is correct.

**7. Launch-target correctness / world safety — `wind_matrix`. N/A.**

`wind_matrix` does not declare `SITL_TARGET`/`GAZEBO_TARGET`; its
`environment.py` launches conditionally on `config.launch_stack` and can
attach to an already-running stack. Its world concern is the SDF wind world,
which is tested by `test_wind_matrix_world_safety.py`.

## Summary

- **2 real gaps**, both in `airspeed_failure`: MAVLink contract (larger and
  more serious) and launch-target correctness.
- **2 covered elsewhere**, both worth knowing because a per-lane conformance
  check globbing `test_<lane>_*` would misreport them as missing.
- **3 not applicable**, of which one (readiness) is a method-design question
  rather than a settled non-applicability.

The original hypothesis — that `test_gps_failure_readiness.py` and
`test_gps_failure_launch_targets.py` have no counterpart because of a coverage
gap rather than a domain difference — holds for launch targets and does not
hold for readiness, where the capability itself is absent from the other two
lanes.

## Explicitly not done

No test was added, modified, weakened, or skipped. `pytest tests/unit
tests/integration` reports 553 passed / 506 subtests, unchanged from before
Stage 1. Filling any gap in this table is separate work requiring Ahmed's
prioritisation.

## Note on a stale expectation

The task specified 541 passing tests as the invariant. The measured baseline
on this branch before any change was **553 passed, 506 subtests**, and it is
identical after. The 541 figure appears to predate commits on
`feature/gps-failure-behavior`; 553 is the number that was actually held
constant.
