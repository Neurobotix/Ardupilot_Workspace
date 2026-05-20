# Phase 5 Gazebo Plugin Fallback Incident

Date/time: 2026-05-21, Africa/Cairo / EEST (+03:00)

## Scope

This audit note records the wind mismatch found after the Phase 5 strict-review
audit-gap remediation run. It documents the exact failing run, the Gazebo
plugin selection failure, the relation to the previously solved production
workspace issue, and the corrected `workspace_next` recheck.

The production workspace at `/home/ahmed/ardupilot_workspace` was read as a
reference only.

## Summary

The Phase 5 remediation run at
`var/runs/phase5_live_rr_parity_remediation_20260521/` is not valid
ArduPilot-side wind parity evidence.

That run requested `wind_x_04_y_04` and passed strict Gazebo topic echo
verification, but its run config records no workspace-built Gazebo plugin. The
only plugin path available to Gazebo was the installed fallback:

```text
/usr/local/lib/ardupilot_gazebo
```

This repeats the already known failure class from the production-era archived
root-cause note
`docs/archive/src_docs/wind_matrix_scripts/09_matrix_launcher_environment_root_cause.md`:
Gazebo world wind publication can look correct while the aircraft plugin and
airspeed path are not equivalent to the known-good stack used by ArduPilot.

## Failing Run

Failing output:

```text
var/runs/phase5_live_rr_parity_remediation_20260521/
```

Failing attempt record:

```text
var/runs/phase5_live_rr_parity_remediation_20260521/
  wind_x_04_y_04/runs/attempt_001/
```

The command was:

```text
timeout 2700s bash -lc 'PYTHONPATH=src:src/sim_ard_gaw/compat_scripts /home/ahmed/ardupilot_workspace/env/bin/python3 -m test_suite.cli.run_round_robin --x-values 4 --y-values 4 --focus-combo wind_x_04_y_04 --runs-per-combo 1 --max-passes 1 --slot-minutes 40 --param-local /home/ahmed/ardupilot_workspace/.private/config/plane_params.local.parm --campaign-root var/runs/phase5_live_rr_parity_remediation_20260521'
```

That command was part of the Phase 5 strict-review audit-gap remediation. Its
manifest/status/provenance behavior still exercises the hardened Phase 5 path,
but it was not a self-contained `workspace_next` invocation and it did not
load the `workspace_next` Gazebo plugin build.

The failing `run_config.json` records:

```text
GZ_SIM_SYSTEM_PLUGIN_PATH=/usr/local/lib/ardupilot_gazebo
workspace plugin file=/home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo/libArduPilotPlugin.so
workspace plugin exists=false
installed plugin sha256=79a2a41cd2e68e979b0196002fb2d2345b66f19dd2493045d5f72bb2e206921f
```

Therefore Gazebo could only load the installed plugin fallback for that run.

## Why The Symptom Matters

Gazebo wind topic echo does not prove the wind signal seen by ArduPilot. The
failing Phase 5 remediation run shows that separation directly:

| Run | Plugin path used | Requested wind | `XKF2 C=0` mean `VWN` | `XKF2 C=0` mean `VWE` |
| --- | --- | --- | --- | --- |
| Broken Phase 5 remediation | installed fallback only | `4,4` | `0.364` | `0.382` |
| Production `017_params_old_009_matrix_r3_plugin_fixed` reference | production workspace build first | `4,4` | `3.909` | `3.965` |

The broken run therefore cannot support a parity claim that injected wind
reached the ArduPilot estimate with the same behavior as the known-good
production plugin-fixed stack.

## Runtime Selection Rule

`src/sim_ard_gaw/compat_scripts/run_one.py` and the production counterpart use
the same search order when a workspace plugin build exists:

```text
workspace build/ardupilot_gazebo first
/usr/local/lib/ardupilot_gazebo second
```

`workspace_next` only prepends its build path if this file exists:

```text
/home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo/libArduPilotPlugin.so
```

It was absent when the broken Phase 5 remediation run started. The code did not
fail closed. It used the fallback, and the fallback reproduced the low-wind
symptom.

## Plugin Builds Checked

After the failure was diagnosed, the `workspace_next` Gazebo plugin was built:

```text
cmake -S src/ardupilot_gazebo -B build/ardupilot_gazebo -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build/ardupilot_gazebo -j2
```

Observed `libArduPilotPlugin.so` hashes after that build:

| Location | SHA-256 |
| --- | --- |
| `workspace_next` build | `1d4089bb6306ecc602e484e9b4e3e77dfb7ecf6649a4292ba872f6d420415fc0` |
| Production workspace build | `df84b40c0eecd257eee53dafae26b023ba795629fcb60354ed4235e08a51a482` |
| Installed `/usr/local` fallback | `79a2a41cd2e68e979b0196002fb2d2345b66f19dd2493045d5f72bb2e206921f` |

The key correction is the selected path order. After the build,
`workspace_next` reports:

```text
/home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo:/usr/local/lib/ardupilot_gazebo
```

The production workspace reports the matching ownership order:

```text
/home/ahmed/ardupilot_workspace/build/ardupilot_gazebo:/usr/local/lib/ardupilot_gazebo
```

## Corrected Recheck

Corrected raw output:

```text
var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/
```

The interrupted `attempt_001` in that directory is not the comparison attempt.
The completed comparison attempt is:

```text
var/runs/phase5_live_rr_workspace_plugin_recheck_20260521/
  wind_x_04_y_04/runs/attempt_002/
```

The corrected command used the `workspace_next` interpreter:

```text
PYTHONPATH=src:src/sim_ard_gaw/compat_scripts /home/ahmed/ardupilot_workspace_next/env/bin/python3 -m test_suite.cli.run_round_robin --x-values 4 --y-values 4 --focus-combo wind_x_04_y_04 --runs-per-combo 1 --max-passes 1 --slot-minutes 40 --param-local /home/ahmed/ardupilot_workspace/.private/config/plane_params.local.parm --campaign-root var/runs/phase5_live_rr_workspace_plugin_recheck_20260521
```

The completed `attempt_002/run_config.json` records:

```text
GZ_SIM_SYSTEM_PLUGIN_PATH=
  /home/ahmed/ardupilot_workspace_next/build/ardupilot_gazebo:
  /usr/local/lib/ardupilot_gazebo
workspace plugin exists=true
workspace plugin sha256=1d4089bb6306ecc602e484e9b4e3e77dfb7ecf6649a4292ba872f6d420415fc0
```

The completed attempt reported `success_full`, completed analysis, and restored
the expected ArduPilot-side wind behavior:

| Run | `XKF2 C=0` mean `VWN` | `XKF2 C=0` mean `VWE` |
| --- | --- | --- |
| Corrected `workspace_next` attempt 002 | `3.845` | `3.882` |
| Production plugin-fixed reference | `3.909` | `3.965` |

## Evidence Commands

Key diagnostic commands used:

```text
jq '.gazebo_plugin_runtime' <attempt>/run_config.json
sha256sum build/ardupilot_gazebo/libArduPilotPlugin.so /usr/local/lib/ardupilot_gazebo/libArduPilotPlugin.so /home/ahmed/ardupilot_workspace/build/ardupilot_gazebo/libArduPilotPlugin.so
PYTHONPATH=src/ardupilot/modules/mavlink /home/ahmed/ardupilot_workspace_next/env/bin/python3 src/ardupilot/modules/mavlink/pymavlink/tools/mavlogdump.py --format csv --types XKF2 <BIN>
```

The `XKF2` CSV summaries filtered `C=0` and compared mean `VWN` and `VWE`
between the broken remediation BIN, corrected recheck BIN, and production
plugin-fixed reference BIN.

## Consequences

- Do not use
  `var/runs/phase5_live_rr_parity_remediation_20260521/` or its curated copy as
  ArduPilot-side wind parity proof.
- Use the completed corrected recheck attempt above when documenting the
  `workspace_next` plugin-selection correction.
- Treat strict Gazebo topic echo verification as necessary but insufficient for
  this failure class.
- Keep an open migration issue until evidence-producing wind-matrix runs fail
  closed or are otherwise governed when the workspace Gazebo plugin build is
  missing and only the installed fallback remains.
