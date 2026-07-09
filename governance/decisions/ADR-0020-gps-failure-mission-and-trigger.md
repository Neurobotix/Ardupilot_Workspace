# ADR-0020: GPS Failure Mission Design And Injection Trigger

Status: Proposed

Date: 2026-07-06

The GPS failure lane uses a purpose-built long one-way mission and inherits the
airspeed lane's first-edge-latched injection trigger.

Decision:

- New `assets/missions/gps_failure_behavior_mission.waypoints`, based on the long
  one-way airspeed mission
  `airspeed_failure_eastbound_long_speed_15_mission.waypoints` (36 km WP3→WP4
  straight leg), with three deliberate changes:
  - Much longer straight leg: GPS slow-drift needs time to accumulate (at 0.5
    m/s the belief walks ~45 m in 90 s). A very long straight cruise lets even
    the slowest rate develop, and lets a fast-rejected glitch and its reset both
    be observed on one heading.
  - No reciprocal leg, no RTL: GPS does not care about wind sign (airspeed needed
    the West leg because wind flips `ARSP−GPS`); the monitor stops after the
    schedule.
  - Injection stays `seq 4`: the seq-1..4 front-half and the seq-4 injection edge
    are preserved from the airspeed missions, so the plugin's first-edge-latch
    logic transfers unchanged.
- Trigger: inject on the first `MISSION_CURRENT` with `seq == 4` after confirmed
  front-half progress (seq 1..3 in AUTO while armed), first-edge latched, never
  re-fired. A missed/late trigger is `pre_injection_failure`, not a late
  injection. Record requested vs actual.

Full reasoning and alternatives:
`governance/runbooks/features/gps_failure_behavior/design_adrs.md`
("ADR (Proposed): Mission Design And Injection Trigger").

Open validation (Phase 1/2): realized straight-leg duration; final waypoint
list and confirmed `seq`-4 geometry.
