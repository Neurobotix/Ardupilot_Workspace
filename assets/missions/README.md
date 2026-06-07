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
