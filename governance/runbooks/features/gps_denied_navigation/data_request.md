# GPS-Denied Navigation Study: Data Request

Oct 6, 2026 · @Ahmed

## Purpose

We need the items below to measure how well the aircraft navigates without GPS, before any test flight. Most of it already exists (numbers, a param file, old logs), so no new flights are needed for sections A to D.

Tick each item when sent. If an item is unknown or unavailable, write that next to it instead of skipping it.

## A. Aircraft performance

- [ ] A1. Cruise airspeed (m/s)
- [ ] A2. Stall speed (m/s)
- [ ] A3. Endurance at cruise (minutes)
- [ ] A4. Typical mission altitude above ground (m)
- [ ] A5. Maximum wind you are allowed to fly in (m/s)
- [ ] A6. Takeoff weight with battery and payload (kg)
- [ ] A7. Wingspan (m), and wing area (m²) if known

## B. Hardware

- [ ] B1. Flight controller model
- [ ] B2. Airspeed sensor model
- [ ] B3. Compass: model, and is it the internal one or an external one (in the GPS module, for example)?
- [ ] B4. Compass placement: distance in cm from the compass to the motor, the ESC, and the main battery wires
- [ ]

## C. Configuration

- [ ] C1. ArduPilot version running on the aircraft
- [ ] C2. Full parameter file as it flies today
- [ ]

## D. Flight logs

This is the most important section: we can test GPS-denied navigation on these logs without flying.

- [ ] D1. 3 to 5 dataflash logs (.bin files from the SD card, not telemetry .tlog files) from recent normal flights
- [ ] D2. Each log at least 10 minutes of flight, with the airspeed sensor working
- [ ] D3. Between them, the logs include straight legs, turns, at least one loiter circle, and climbs or throttle changes
- [ ] D4. For each log, one line: date, location, approximate wind that day (speed and direction if known), and any problems during the flight
- [ ] D5. Value of `LOG_REPLAY` and `LOG_DISARMED` at the time of these flights (also in the param file, if it is from the same period)

## E. Logging for future flights

One small change so every future flight can be used for this study. It does not affect how the aircraft flies, only what it records.

- [ ] E1. Set `LOG_REPLAY = 1` and `LOG_DISARMED = 1`, then confirm the next flight's log is larger than usual (it records more sensor data)
- [ ] E2. Check the SD card has enough free space for the larger logs

## Delivery

Put everything in one shared folder, named by section (for example `D1_log_2026-09-14.bin`, `C2_params.param`, `B5_compass_photo.jpg`). Short answers can go directly in this doc next to each item.

- Folder link: (to fill)
- Deadline: (to fill)
- Questions: Ahmed
