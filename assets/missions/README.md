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
- `gps_failure_behavior_mission.waypoints`
  Purpose: active GPS failure behavior mission. It preserves the locked
  seq-1..4 front half and explicit `DO_CHANGE_SPEED=15`, injects on the first
  seq-4 edge, then provides an approximately 36 km one-way Eastbound
  measurement leg with no reciprocal leg, RTL, or landing sequence. Static
  structure is validated; realized flight duration remains a Phase-2 item.
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
