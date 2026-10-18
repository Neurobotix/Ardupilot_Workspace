# Mission Library

Active waypoint missions live directly in this directory.

## Active Missions

- `airspeed_validation_mission.waypoints`
  Purpose: reciprocal-leg airspeed INTEGRATION validation in wind (legacy; not
  the fault-injection lane).
- `airspeed_failure_behavior_mission.waypoints`
  Purpose: airspeed fault-injection behavior lane. 100 m cruise, 800 m reciprocal
  East/West measurement legs, fault injected on entering seq 4, ends in RTL (no
  landing sequence). See
  `governance/runbooks/features/airspeed_failure_behavior/`.
- `airspeed_failure_headwind_ramp_mission.waypoints`
  Purpose: positive reported-airspeed stepped-ramp variant for the airspeed
  fault-injection behavior lane. 100 m cruise, longer Eastbound climb/settle
  runway, one 23000 m continuous headwind line holder, ramp schedule starts on
  entering seq 4, and the monitor finishes after the case-specific final ramp
  observation (`+100%` standard or `+200%` extended) with no RTL waypoint.
- `airspeed_failure_headwind_pulse_ladder_mission.waypoints`
  Purpose: positive reported-airspeed pulse-ladder variant for the airspeed
  fault-injection behavior lane. 100 m cruise, longer Eastbound climb/settle
  runway, one 23000 m continuous headwind line holder, pulse schedule starts
  on entering seq 4, and the monitor finishes after the final observation with
  no RTL waypoint.
- `airspeed_failure_eastbound_long_speed_15_mission.waypoints`
  Purpose: direction-neutral 36 km Eastbound measurement geometry for new
  headwind/tailwind studies whose intended speed source is an explicit
  `DO_CHANGE_SPEED=15` command. Injection remains on entering seq 4; the
  monitor stops the run and the mission has no RTL waypoint.
- `airspeed_failure_eastbound_long_cruise_follow_mission.waypoints`
  Purpose: the same direction-neutral 36 km geometry without
  `DO_CHANGE_SPEED`, so the selected overlay's `AIRSPEED_CRUISE` is the sole
  cruise-speed source. Seq numbering and the seq-4 injection contract match
  the speed-15 variant.
- `shahin_e_gate4_climb_descent.waypoints`
  Purpose: Shahin-E model validation Gate 4 independent check (no tuning). Same
  takeoff and climb as Gate 3, then a 0.93 m/s climb 200 -> 300 m over 1830 m and,
  after 1 km level, a 0.53 m/s descent 300 -> 200 m over 3200 m (AUTO glide slope
  at 17 m/s), then 1 km level and a loiter. No RTL and no landing.
- `shahin_e_gate3_level_cruise.waypoints`
  Purpose: Shahin-E model validation Gate 3 calibration flight. Same takeoff and
  climb as Gate 2, then one continuous 6 km straight level Eastbound leg at 200 m
  and 17 m/s (about 350 s, measured with `shahin_flight_envelope.py`), then a
  loiter over the leg end. No RTL and no landing.
- `shahin_e_gate2_first_flight.waypoints`
  Purpose: Shahin-E model validation Gate 2 first flight (gps_denied_navigation).
  Takeoff to 50 m with the real takeoff values, climb to 200 m, a 3 km straight
  level Eastbound record leg, a 180 deg turn and 3 km back, then an unlimited
  loiter over home at 200 m. No RTL and no landing. See
  `governance/runbooks/features/gps_denied_navigation/shahin_e_model_sources.md`.
- `gps_failure_behavior_mission.waypoints`
  Purpose: active GPS failure behavior shorter final-science candidate. It uses a
  1000 m controlled baseline, injects on the first seq-4 edge, observes the
  fault on a 6000 m straight Eastbound leg, continues straight for 1000 m of
  recovery/continuation, holds a 30 s terminal loiter, and ends in RTL at seq 9.
  The minimum post-injection window is an evidence gate; it does not terminate
  the flight.
- `gps_failure_behavior_mission_fast_cruise_18mps.waypoints`
  Purpose: mission half of the GPS failure `fast_cruise_18mps` envelope. It
  preserves the active v6 geometry, seq-4 trigger contract, terminal loiter,
  seq-8 terminal gate, and seq-9 RTL, but raises the explicit
  `DO_CHANGE_SPEED` command from 15 m/s to 18 m/s. The complete envelope also
  requires `config/overlays/plane_gps_airspeed_fast_cruise_18mps.parm` and
  `assets/worlds/mini_talon_gps_airspeed_runway.sdf`.
- `lidar_staircase_mission.waypoints`
  Purpose: LiDAR overpass mission for the staircase world.
- `quad_star_showcase_mission.waypoints`
  Purpose: Iris quadcopter showcase mission that traces a five-point star and
  returns to launch.
- `runway_autoland_gentle_approach_v8.waypoints`
  Purpose: retained runway autoland mission from the landing-tuning cycle.
- `square_500m_five_laps_loiter5_land.waypoints`
  Purpose: 100m climb, five square laps, five-turn home loiter, then land.

## Archive

Historical mission variants and tuning snapshots live in `archive/`.
These are kept for comparison and traceability, not as the default working set.
