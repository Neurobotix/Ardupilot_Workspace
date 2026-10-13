# GPS-Denied Navigation Study: Project Plan

Oct 12, 2026 · @Ahmed

## Goal and success criteria

The study must show how far and how long our fixed-wing aircraft can fly without GPS, using only IMU, compass, baro, and airspeed, and still arrive within an acceptable error.

Success is defined as: fly **T minutes** without GPS and end with position error below **E meters**. T and E are not set yet (see Open decisions). Until they are, results are reported against three tiers:

| Tier | Denial duration | Error target |
| --- | --- | --- |
| 1 | 1 min | (to set) |
| 2 | 5 min | (to set) |
| 3 | 15 min | (to set) |

## Phases

Each phase starts only when the previous one meets its exit criterion.

1. **Phase 0: Data collection.** Engineers send aircraft specs, param file, and flight logs ([data request](data_request.md); shared copy: https://claude.ai/code/artifact/78854d82-603f-48b0-b375-890e9ad87ceb).
   - Exit: all items in sections A to D received or marked unavailable.
2. **Phase 1: Measure.** Two tracks in parallel, both zero-risk:
   - Log analysis on existing flights: wind estimate vs GPS-derived wind, airspeed calibration, compass heading vs throttle.
   - SITL campaigns with GPS removed mid-flight (test matrix below). Can start before Phase 0 ends with the default plane model, then rerun with our aircraft's weight and wing.
   - Exit: error vs time known for every scenario, and the largest error source identified.
3. **Phase 2: Improve.** Target only the largest error source from Phase 1 (wind estimation, airspeed calibration, or heading).
   - Exit: SITL meets the chosen tier, or the limit is understood and documented.
4. **Phase 3: Prove outdoors.** Real flights with GPS logged as ground truth but not used by the EKF, switched by an RC switch (EKF source sets).
   - Exit: the chosen tier met in real flight, repeated at least 3 times.

## Phase 1 test matrix

GPS is removed at a fixed point before the maneuver; the run continues on dead reckoning.

| # | Scenario | What it exposes |
| --- | --- | --- |
| S1 | Straight cruise: into, with, and across the wind | Wind estimate error, airspeed scale error |
| S2 | 90° turn | Wind error seen from a new direction after the turn |
| S3 | 180° reversal | Airspeed scale error (shows up as asymmetry) |
| S4 | Loiter circle | Constant curvature; all wind directions in one run |
| S5 | Climb, descent, throttle changes | Compass interference from motor current, wind change with altitude |
| S6 | Wind changes after GPS loss | The EKF cannot know the wind changed; closest to real conditions |

Each scenario runs across:

- Wind speed: 0, 5, 10 m/s
- Wind direction: 0°, 90°, 180° relative to the first leg
- Denial duration: 30 s, 1, 2, 5 min
- Injected faults (SITL only): compass offset, airspeed calibration error, motor interference on compass

## Metrics

Every run reports the same five numbers so runs can be compared directly.

- Position error vs time since GPS loss (m)
- That error split into along-track and cross-track (m)
- Heading error (deg)
- Wind estimate error: EKF wind vs true wind (m/s)
- Error at the end of the denial window, compared with the tier target

Ground truth: the simulator's true state in SITL; standard GPS logging outdoors. Standard GPS (2 to 3 m) is accurate enough because expected drift over minutes is tens to hundreds of meters, so RTK is not needed.

## Outdoor safety rules

GPS is never actually lost: it stays on and logged, and one switch returns the EKF to it.

- Every test procedure is run in SITL first, including the source switch.
- Denial duration grows in steps (30 s, 1 min, 2 min, 5 min); move up only if the previous step stayed within its error budget.
- Abort and switch back to GPS if position error passes a set limit (to define per step).
- Geofence enabled on every flight.
- Pilot ready to take over in a mode that does not need position (for example FBWA or MANUAL).
- Fly only in steady, light wind; record wind before each flight.
- Open area, safe altitude, low speed for the first flights.

## Roles

| Role | Who | Responsibilities |
| --- | --- | --- |
| Study lead | Ahmed | Defines tests and targets, runs SITL and log analysis, decides go / no-go between phases |
| Field engineers | (names to fill) | Provide data and logs, run outdoor flights per procedure, send logs after every flight |
| Safety pilot | (name to fill) | Takes over on any abort, has final say on whether a flight happens |

## Open decisions and risks

- [ ] **Mission target (T, E).** Depends on why and where GPS would be lost in real use. Needed before Phase 2 ends.
- [ ] **Abort limits per outdoor step.** Set from Phase 1 results.

* Risk: old logs were likely recorded without `LOG_REPLAY`, so full EKF replay may only work on new logs. Basic log analysis still works.
* Risk: SITL results depend on how close the sim model is to our aircraft; reruns needed once weight and wing data arrive.
* Risk: wind outdoors is never known exactly, so wind-related errors are harder to separate in Phase 3 than in SITL.

## Task tracker

Update the Status column as work moves; add rows for new tasks.

| # | Task | Phase | Owner | Status |
| --- | --- | --- | --- | --- |
| T1 | Fill folder link and deadline in the data request, send it | 0 | Ahmed | Not started |
| T2 | Return data request items A to D | 0 | Field engineers | Not started |
| T3 | Enable `LOG_REPLAY` and `LOG_DISARMED` on the aircraft | 0 | Field engineers | Not started |
| T4 | Set provisional mission target (T, E) | Decision | Ahmed | Not started |
| T5 | Set up SITL plane with EKF source switch for GPS denial | 1 | Ahmed | Not started |
| T6 | Build analysis script for the five metrics | 1 | Ahmed | Not started |
| T7 | Run S1 to S6 matrix on the default plane model | 1 | Ahmed | Not started |
| T8 | Analyze old logs: wind, airspeed, compass vs throttle | 1 | Ahmed | Not started |
| T9 | Rerun matrix with our aircraft's weight and wing | 1 | Ahmed | Not started |
| T10 | Phase 1 report: largest error source | 1 | Ahmed | Not started |
| T11 | Improve largest error source, verify in SITL | 2 | Ahmed | Not started |
| T12 | Write outdoor procedure and abort limits | 3 | Ahmed | Not started |
| T13 | Outdoor flights, 30 s up to 5 min denial | 3 | Field engineers, safety pilot | Not started |
