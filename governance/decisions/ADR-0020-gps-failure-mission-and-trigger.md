# ADR-0020: GPS Failure Mission Design And Injection Trigger

Status: Proposed

Date: 2026-07-06

The GPS failure lane uses an airspeed-style bounded smoke mission and inherits
the airspeed lane's first-edge-latched injection trigger.

Decision:

- `assets/missions/gps_failure_behavior_mission.waypoints` uses the practical
  airspeed behavior lifecycle: pre-injection settle, 2000 m Eastbound
  measurement leg, reciprocal return leg, and RTL at seq 9. GPS owns its exact
  geometry rather than importing the airspeed asset. The earlier 36 km one-way
  design is retired for nominal smoke because it made the live experiment
  unnecessarily slow.
- Injection stays `seq 4`: the seq-1/3 front-half and the seq-4 injection edge
  are preserved from the airspeed missions, so the plugin's first-edge-latch
  logic transfers unchanged.
- Trigger: inject on the first `MISSION_CURRENT` with `seq == 4` after confirmed
  navigation progress through seq 1 and seq 3 in AUTO while armed, first-edge
  latched, never re-fired. Seq 2 is `DO_CHANGE_SPEED`; it is accepted when
  reported but is not required because ArduPlane may execute DO commands
  without publishing them as `MISSION_CURRENT`. A missed/late trigger is
  `pre_injection_failure`, not a late injection. Record requested vs actual.

Full reasoning and alternatives:
`governance/runbooks/features/gps_failure_behavior/design_adrs.md`
("ADR (Proposed): Mission Design And Injection Trigger").

Open validation (Phase 1/2): realized straight-leg duration; final waypoint
list and confirmed `seq`-4 geometry.

Amendment (2026-07-14): a rejected raw diagnostic run emitted
`MISSION_CURRENT` as `0 -> 1 -> 3 -> 4`; seq 2 was never emitted. Mission
identity verification had already proved the seq-2 `DO_CHANGE_SPEED` item was
uploaded correctly. The trigger therefore requires navigation seqs 1 and 3,
permits an optional seq 2, and retains all armed/AUTO/freshness/monotonicity
checks. This corrects an unreachable telemetry precondition; it does not accept
the smoke or authorize another run.

Amendment (2026-07-14, second trigger correction): a governed nominal attempt
showed that the monitor begins while `MISSION_CURRENT` still reports home row
seq 0. Leading seq-0 reports are not navigation evidence and are ignored until
seq 1 begins the trigger trace. A seq-0 report after seq 1 remains a regression
and fails closed.

Amendment (2026-07-14, mission-lifecycle correction): the rejected nominal root
`var/runs/gps_failure_behavior_20260714T113259746238Z/` proved that the GPS
monitor had not preserved the airspeed-style terminal contract. The minimum
post-injection duration is an evidence-eligibility gate, not an experiment stop
condition. Normal GPS attempts continue through the remaining mission and stop
after AUTO transitions to RTL at or beyond seq 8 and RTL remains stable for
10 s. Early RTL or a genuine loss-of-control terminal is recorded separately;
an incomplete nominal attempt is never accepted. `MISSION_ITEM_REACHED`, maximum
sequence, the AUTO-to-RTL sequence, and the terminal reason are required mission
progress evidence. The exact first validated seq-4 event is immutable and is
the primary post-flight analysis anchor; repeated `MISSION_CURRENT seq=4`
messages cannot replace it.

Amendment (2026-07-14, calm-lane takeoff geometry): reviewed BIN data from raw
nominal root `var/runs/gps_failure_behavior_20260714T120212630044Z/` showed
takeoff completing at 98.22 m AGL when the aircraft was approximately 323 m
East. The copied 300 m seq-3 settle waypoint was then behind the aircraft and
outside `WP_RADIUS=20`, so target bearing reversed and produced a full
pre-injection turnback loop. Mission v3 moves seq 3/7 from 300 m to 500 m East
and seq 4/5/6 from 1100 m to 1300 m East. Both measurement legs remain 800 m,
seq numbers and the first seq-4 trigger are unchanged, and the 100 m safety
altitude is retained. The v2 raw result remains historical; v3 requires a fresh
nominal validation before a fault case. That validation completed on 2026-07-14
at `var/runs/gps_failure_behavior_20260714T122459635208Z/`: the run carried the
v3 hash, completed through seq 9 and planned RTL, and traveled monotonically
East from takeoff completion to seq 3 with maximum absolute roll of 2.1 degrees.
The result is raw validation, not curated Phase-2 evidence.

Amendment (2026-07-14, longer/wider fault geometry): mission v4 retains the
validated 500 m settle point, seq numbering, first seq-4 injection edge, 100 m
altitude, and planned RTL. It moves seq 4/5/6 to 2500 m East and increases the
reciprocal-lane offset to 500 m North, producing 2000 m outbound and reciprocal
measurement legs. This gives the first fault cases more post-injection distance
without returning to the retired 36 km open-ended mission. Active mission
SHA-256 is
`8d1c8de43c6e496946b1f6bdf3d88f4aa14cd3ba7abe84067cb6a4edd27d7f35`.
V4 has structural/no-live geometry validation only; the v3 raw nominal remains
the latest live geometry result.
