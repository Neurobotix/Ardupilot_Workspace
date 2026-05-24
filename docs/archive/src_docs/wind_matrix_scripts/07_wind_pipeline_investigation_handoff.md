# Wind Pipeline Investigation Handoff

> Update after the final 12/12 A/B test:
> this document is historical investigation context, not the final root-cause
> answer for the automated matrix mismatch. The resolved cause is documented in
> [09 Matrix Launcher Environment Root Cause](09_matrix_launcher_environment_root_cause.md).
> The decisive finding was that `run_matrix.py` / `run_matrix_round_robin.py`
> launched Gazebo with an inherited `GZ_SIM_*` environment built via
> `setdefault()`, while the working manual stack used `launch.sh` to
> deterministically prepend the correct Gazebo plugin/resource paths.

This document is a full handoff of the wind / airspeed / preloaded-world investigation performed in this workspace. It is written for another AI agent or engineer who needs to continue from here without redoing the entire archaeology pass.

The goal is not just to summarize conclusions, but to preserve:

- what was inspected
- what was actually tested
- what evidence supports each claim
- what remains unresolved
- what is likely stale documentation versus a real system bug

## Scope

The investigation focused on the interaction between:

- `run_one.py` wind handling
- `run_matrix.py` preloaded world generation
- Gazebo world wind configuration
- Gazebo `air_speed` sensor behavior
- `ArduPilotPlugin` airspeed ingestion
- bench worlds versus runway world behavior

Primary files inspected:

- [run_one.py](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_one.py:180)
- [run_matrix.py](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_matrix.py:1)
- [launch.sh](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh:76)
- [mini_talon_wind_runway.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/mini_talon_wind_runway.sdf:30)
- [mini_talon_wind_bench.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/mini_talon_wind_bench.sdf:1)
- [bench_s1_airspeed.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/bench_s1_airspeed.sdf:1)
- [mini_talon_with_airspeed/model.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/models/mini_talon_with_airspeed/model.sdf:329)
- [wind_sensor_probe/model.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/models/wind_sensor_probe/model.sdf:1)
- [wind_sitl_probe/model.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/models/wind_sitl_probe/model.sdf:1)
- [ArduPilotPlugin.cc](/home/ahmed/ardupilot_workspace/src/ardupilot_gazebo/src/ArduPilotPlugin.cc:352)
- [airspeed_claim_probe.py](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/airspeed_claim_probe.py:77)
- [TEST_RESULT_2026-02-04.md](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/003_Plane_Airspeed/TEST_RESULT_2026-02-04.md:1)
- [TEST_RESULT_2026-04-02.md](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md:1)

## Executive Summary

### High-confidence findings

1. `run_one.py` supports two different wind-setting modes:
   - runtime topic publication via [inject_wind()](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_one.py:782)
   - preloaded archived SDF validation via [preloaded_wind_artifact()](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_one.py:871)

2. `run_matrix.py`'s preloaded-world path rewrites only the root `<wind><linear_velocity>` text in the world SDF via [write_static_wind_world()](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_matrix.py:130).

3. `preloaded_wind_artifact()` is a weak validator. It proves only that the archived SDF file contains the requested vector. It does not prove Gazebo used that vector at runtime. See [run_one.py](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_one.py:860).

4. The strong claim that "`WindEffects` forces preloaded wind to zero" is not supported by the runtime probes performed here.

5. The deepest inconsistency uncovered is not preloaded wind zeroing. It is a sign/semantics contradiction between:
   - bench documentation expecting negative Gazebo `diff_pressure`
   - current `ArduPilotPlugin` code zeroing all non-positive `diff_pressure`

6. There is historical evidence of workflow drift:
   - older project notes describe a Python bridge-based airspeed path
   - current aircraft model uses direct `ArduPilotPlugin` subscription to `/airspeed`

### Current best diagnosis

Superseded for the matrix automation failure. See
[09 Matrix Launcher Environment Root Cause](09_matrix_launcher_environment_root_cause.md).

The system is conflating three different validation questions:

1. Does the SDF file contain the requested wind vector?
2. Does Gazebo apply that vector as live world wind?
3. Do the sensor and ArduPilot consume that wind correctly?

Those are not equivalent, and several project docs treat them as if they were.

## System Design As Confirmed

### Wind source

The intended wind source for the CTE workflow is Gazebo, not SITL internal wind.

Evidence:

- [mini_talon_wind_runway.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/mini_talon_wind_runway.sdf:30) explicitly documents startup wind baked into `<linear_velocity>`.
- `plane_airspeed.parm` was previously observed to zero SITL wind parameters during the broader investigation.
- [launch.sh](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh:99) prepends Gazebo resource/plugin paths to support the Gazebo-native path.

### Two wind-setting modes

#### 1. Runtime injection

[inject_wind()](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_one.py:782):

- publishes `gz.msgs.Wind` to `/world/mini_talon_wind_runway/wind/`
- can optionally run strict topic echo verification

This path verifies the publish step better than the preloaded path.

#### 2. Preloaded world

[write_static_wind_world()](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_matrix.py:130):

- reads [mini_talon_wind_runway.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/mini_talon_wind_runway.sdf:1)
- regex-replaces the first `<wind><linear_velocity>...`
- writes a per-attempt SDF

[preloaded_wind_artifact()](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_one.py:871):

- reparses the archived SDF text
- compares it to requested `(x, y, 0)`
- returns `"status": "ok"` if file contents match

This does not validate live world state.

## Key Code Evidence

### 1. Preloaded path edits only root `<wind>`

See [run_matrix.py](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_matrix.py:130):

```python
replacement = rf"\g<1>{x_wind:.3f} {y_wind:.3f} 0.000\g<3>"
rendered, count = WIND_LINEAR_VELOCITY_RE.subn(replacement, source, count=1)
```

It does not edit the `WindEffects` plugin block.

### 2. Preloaded validation is file-based

See [run_one.py](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_one.py:860):

```python
parsed_wind = parse_sdf_world_wind(archived_world)
...
"verification": "Gazebo was launched from an archived SDF whose <wind><linear_velocity> matches the requested combo."
```

This is a filesystem assertion, not a runtime assertion.

### 3. World file explicitly intends static startup wind to work

See [mini_talon_wind_runway.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/mini_talon_wind_runway.sdf:30).

Important parts:

- root `<wind>` block at lines 46-48
- `WindEffects` plugin at lines 50-68
- explanatory comment stating automated runners bake test wind into `<linear_velocity>`

This does not prove the design is correct, but it does show the repo author intended preloaded startup wind to be a first-class path.

### 4. `ArduPilotPlugin` rejects non-positive `diff_pressure`

See [ArduPilotPlugin.cc](/home/ahmed/ardupilot_workspace/src/ardupilot_gazebo/src/ArduPilotPlugin.cc:352):

```cpp
double diff_pressure = _msg.diff_pressure();
if (diff_pressure > 0) {
  airspeedValue = std::sqrt(2.0 * diff_pressure / 1.225);
} else {
  airspeedValue = 0.0;
}
```

This is the core sign-handling fact.

### 5. Bench world expects magnitude-style Gazebo behavior

See [mini_talon_wind_bench.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/mini_talon_wind_bench.sdf:12).

The comments explicitly claim:

- `5 0 0 -> 15.3 Pa`
- `10 0 0 -> 61.3 Pa`
- `0 5 0 -> 15.3 Pa`

That means the intended Gazebo-side interpretation is magnitude-based, not simply forward-axis-only.

### 6. Bench S1 claims negative Gazebo pressure but non-zero ArduPilot airspeed

See [bench_s1_airspeed.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/bench_s1_airspeed.sdf:12):

- Gazebo side: `/airspeed -> diff_pressure ≈ -15.3 Pa`
- ArduPilot side: expect `~5 m/s`

This is directly in tension with [ArduPilotPlugin.cc](/home/ahmed/ardupilot_workspace/src/ardupilot_gazebo/src/ArduPilotPlugin.cc:352).

### 7. `wind_sitl_probe` mounts the airspeed sensor with yaw `180`

See [wind_sitl_probe/model.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/models/wind_sitl_probe/model.sdf:38):

```xml
<sensor name="air_speed_sensor" type="air_speed">
  <pose degrees="true">0 0 0 0 0 180</pose>
```

This is a major clue for why a bench might observe negative `diff_pressure`.

### 8. Real aircraft pitot setup is different

See [mini_talon_with_airspeed/model.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/models/mini_talon_with_airspeed/model.sdf:329) and [mini_talon_with_airspeed/model.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/models/mini_talon_with_airspeed/model.sdf:953):

- pitot boom is a dedicated `pitot_link`
- wind is enabled on the pitot link
- `air_speed_sensor` publishes `/airspeed`
- `ArduPilotPlugin` subscribes to `/airspeed`

This means the flight world and the minimal SITL bench are not identical consumers.

## Historical Drift Found In Project Notes

### Older implementation note: Python bridge

[TEST_RESULT_2026-02-04.md](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/003_Plane_Airspeed/TEST_RESULT_2026-02-04.md:1) describes an older architecture involving `airspeed_bridge.py`.

That note is implementation-oriented and does not match the current direct plugin wiring.

### Newer follow-up note: direct end-to-end validation

[TEST_RESULT_2026-04-02.md](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md:1) claims the airspeed chain is validated end to end and discusses:

- startup offset issues
- Gazebo pitot noise isolation
- SITL-side randomization isolation
- reciprocal-leg flight behavior

This newer note may still be broadly true at the flight-behavior level, while some lower-level bench explanations remain stale or contradictory.

## Runtime Probes Performed

All probes below were run locally in this workspace during this investigation.

### Probe A: Wind bench with static `5 0 0`

World:

- [mini_talon_wind_bench.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/mini_talon_wind_bench.sdf:1)

Setup characteristics:

- no ArduPilot
- no LiftDrag
- `WindEffects` active
- `air_speed` sensor only

Observed result:

- `/airspeed` reported roughly `diff_pressure ≈ -15.31 Pa`

Interpretation:

- definitely nonzero wind response
- sign was negative in the observed run
- magnitude matched the 5 m/s dynamic-pressure expectation

### Probe B: Runway-style world with static `-5 0 0`

World:

- `mini_talon_wind_runway_sea_level.sdf`

Observed result:

- `/airspeed` reported roughly `+15.27 Pa`

Interpretation:

- again, clearly nonzero
- sign behavior differed from Probe A
- runway world is not a clean low-noise truth bench

### Probe C: Preloaded runway world with `12 12 0`

Method:

- copied [mini_talon_wind_runway.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/mini_talon_wind_runway.sdf:1) to a temp file
- changed root `<linear_velocity>` to `12 12 0`
- launched Gazebo on the temp world
- sampled `/airspeed`

Observed result:

- about `-90.28 Pa` at sim times roughly `4.64 s` and `8.38 s`

Important context:

- the world uses `time_for_rise = 10` at [mini_talon_wind_runway.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/mini_talon_wind_runway.sdf:55)
- these samples were likely taken before full steady-state

Interpretation:

- preloaded wind did not appear to be zero
- this result does not validate final steady-state `12,12` magnitude cleanly
- runway world plus pitot response is not the right instrument for exact vector validation

### Why `90 Pa` was not enough

For full vector magnitude:

- `sqrt(12^2 + 12^2) = 16.97 m/s`
- expected `q = 0.5 * 1.225 * 16.97^2 ≈ 176.4 Pa`

So `90 Pa` is not evidence of fully validated final `12,12` magnitude.

However, it is also not evidence of zero wind.

This is why the correct conclusion was:

- "preloaded wind not proven zero"
- not "preloaded wind proven fully correct"

### Probe D: Plugin boundary investigation

Attempted method:

- use [airspeed_claim_probe.py](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/airspeed_claim_probe.py:77) to listen for plugin JSON traffic on UDP `9002`

What happened:

- the listener bound `9002`
- `ArduPilotPlugin` then failed to start because it also binds `127.0.0.1:9002`

Observed plugin error:

- `failed to bind with 127.0.0.1:9002 aborting plugin`

What this proved:

- `fdm_port_in=9002` is owned by the plugin
- `ArduPilotPlugin` binds that port and waits for controller packets
- passive sniffing on `9002` is not the correct way to observe outbound plugin JSON unless the handshake is emulated another way

Supporting code:

- [ArduPilotPlugin.cc](/home/ahmed/ardupilot_workspace/src/ardupilot_gazebo/src/ArduPilotPlugin.cc:1326)
- [ArduPilotPlugin.cc](/home/ahmed/ardupilot_workspace/src/ardupilot_gazebo/src/ArduPilotPlugin.cc:1515)
- [ArduPilotPlugin.cc](/home/ahmed/ardupilot_workspace/src/ardupilot_gazebo/src/ArduPilotPlugin.cc:2098)

## Binary / Build Evidence

Two plugin binaries are present:

- `build/ardupilot_gazebo/libArduPilotPlugin.so`
- `/usr/local/lib/ardupilot_gazebo/libArduPilotPlugin.so`

Observed facts:

- SHA256 hashes differ
- both appear to contain `AirspeedCb`
- both appear, from object dump inspection, to branch away from the sqrt path for non-positive `diff_pressure`

Implication:

- this is probably not just "source says one thing, installed binary does another"
- both local plugin copies likely share the same non-positive-pressure rejection logic

## Environment Setup Risk

There is a real environment inconsistency between shell launch paths and Python runtime launch paths.

### `launch.sh`

[launch.sh](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh:99) prepends Gazebo plugin/resource paths carefully using `prepend_path_entry()`.

### `run_one.py`

[runtime_env()](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/run_one.py:180) uses:

```python
env.setdefault("GZ_SIM_RESOURCE_PATH", ...)
env.setdefault("GZ_SIM_SYSTEM_PLUGIN_PATH", ...)
```

Implication:

- if those env vars already exist, `run_one.py` does not merge or prepend required local paths
- this can change which plugins/world assets are actually used
- that matters a lot for interpreting simulator behavior

This is not the main sign bug, but it is a real design weakness and may explain some "works in one launcher path, fails in another" behavior.

## Claims Evaluated

### Claim: `WindEffects` overrides preloaded root wind to zero because noise mean is zero

Status: not supported by the evidence gathered here

Why not supported:

- base world comments explicitly intend startup `<linear_velocity>` + `WindEffects` to work
- bench world also relies on static `<wind>` plus `WindEffects`
- runtime probes showed strong nonzero pressure responses for preloaded cases

What is true instead:

- preloaded validation is weak
- the project lacks a clean runtime world-wind validator

### Claim: `preloaded_wind_artifact()` is insufficient

Status: supported

Why:

- it parses archived SDF text only
- it never queries Gazebo runtime state
- it never queries a live wind entity/vector field

### Claim: bench docs and current plugin code disagree on negative pressure handling

Status: strongly supported

Why:

- [bench_s1_airspeed.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/bench_s1_airspeed.sdf:12) expects negative Gazebo `diff_pressure`
- [ArduPilotPlugin.cc](/home/ahmed/ardupilot_workspace/src/ardupilot_gazebo/src/ArduPilotPlugin.cc:352) zeroes non-positive `diff_pressure`
- [airspeed_claim_probe.py](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/airspeed_claim_probe.py:77) encodes the same non-positive rejection assumption

## What Seems Most Likely

Current best guess is that one or more of the following are true:

1. `bench_s1_airspeed.sdf` comments are stale.
2. The `wind_sitl_probe` sensor orientation changed the sign, but the downstream plugin logic and the explanatory docs were never realigned.
3. The lower-level bench interpretation is wrong, but the higher-level flight validation in [TEST_RESULT_2026-04-02.md](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md:1) is still broadly correct.
4. There is a real airspeed sign bug in the Gazebo-to-ArduPilot chain, partially masked by other effects in full-flight scenarios.

Right now, option 3 or a mix of 2+3 feels most plausible, but it is not settled.

## What Is Proven Versus Not Proven

### Proven enough

- `run_matrix.py` rewrites only root `<wind><linear_velocity>`
- `preloaded_wind_artifact()` validates only SDF text
- runtime preloaded cases can produce clearly nonzero airspeed pressure
- bench docs and plugin sign handling contradict each other
- `wind_sitl_probe` uses a 180-degree airspeed sensor pose
- the project has historical documentation drift around the airspeed path

### Not proven

- that `WindEffects` always forces preloaded wind to zero
- that preloaded `12,12` reaches the exact intended steady-state vector in the runway world
- that the bench negative-pressure expectation is still correct for the current runtime stack
- that the "validated end to end" conclusion is wrong

## Recommended Next Investigation Steps

For the next AI agent, this is the recommended order.

### 1. Settle the bench sign chain

Trace one minimal case end to end:

- `wind_sitl_probe` sensor pose
- Gazebo `/airspeed` sign
- plugin `AirspeedCb`
- JSON state sent by plugin
- what SITL displays

This is the most valuable next step.

The missing piece from this investigation is the plugin outbound JSON after a proper controller handshake. Passive sniffing on `9002` is not sufficient because the plugin owns that bind port and auto-detects the peer from received controller packets.

### 2. Separate world-wind validation from airspeed validation

The project needs independent checks for:

- SDF text correctness
- live Gazebo world wind correctness
- sensor correctness
- ArduPilot ingestion correctness

Right now those are blended together.

### 3. Add a proper runtime preloaded-wind verifier

`preloaded_wind_artifact()` should not be treated as proof of live simulator wind.

Better options:

- query the wind entity / topic at runtime
- add a dedicated world-state probe
- or construct a minimal bench that validates live wind vector components directly

### 4. Audit docs for staleness

Likely stale or partially stale artifacts to audit:

- [bench_s1_airspeed.sdf](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/worlds/bench_s1_airspeed.sdf:1)
- [TEST_RESULT_2026-02-04.md](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/003_Plane_Airspeed/TEST_RESULT_2026-02-04.md:1)

The newer [TEST_RESULT_2026-04-02.md](/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md:1) appears more current, but should still be read critically.

## Suggested Questions For The Next Agent

1. Is negative `/airspeed` in the S1 bench still reproducible with the current plugin selected by the actual launcher path?
2. Does `wind_sitl_probe`'s `180` degree sensor orientation fully explain that sign?
3. After a valid handshake, what `airspeed` value does `ArduPilotPlugin` actually emit in its JSON state packet?
4. Are the build and installed plugin binaries both actually in play depending on launcher path or environment?
5. Is there any Gazebo-native way in this setup to query live world wind vector directly, instead of inferring it from pitot pressure?

## Bottom Line

The most important correction from this investigation is:

- the main problem is not yet proven to be "preloaded wind silently becomes zero"
- the main proven problem is that the project's validation layers are blurred, and the bench airspeed sign story is internally inconsistent

Another way to say it:

The filesystem-level preloaded-world path is under-verified, and the sensor/plugin interpretation path contains a likely stale-or-buggy sign story. Those are different problems, and they should be treated separately.
