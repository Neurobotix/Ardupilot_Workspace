# Flight Modes Reference

> **ARCHIVED — retained as reference.** A workspace-relevant flight-mode quick
> reference is in `docs/architecture/simulation_lanes.md`. This full table is
> kept for completeness. Errata:
> `governance/audits/2026-05-20_phase3_docs_errata.md`.

This document covers the flight modes available in ArduPilot for both fixed-wing (ArduPlane) and multirotor (ArduCopter) aircraft.

## ArduPlane (Fixed-Wing) Modes

### Manual Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `MANUAL` | Direct control, no stabilization | Expert pilots, aerobatics |
| `STABILIZE` | Auto-level when sticks centered | Learning to fly |
| `FBWA` | Fly-By-Wire A - stabilized with manual throttle | **Recommended for testing** |
| `FBWB` | Fly-By-Wire B - stabilized with altitude hold | Cruising |

### Autonomous Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `AUTO` | Follow waypoint mission | Autonomous flights |
| `GUIDED` | Accept external navigation commands | **Good for RL** |
| `LOITER` | Circle at current position | Holding position |
| `RTL` | Return to launch point | Emergency/end of mission |
| `CIRCLE` | Circle around a point | Surveillance |
| `CRUISE` | GPS-guided cruise | Long distance |

### Usage Examples

```bash
# Basic flight
mode FBWA
arm throttle force
rc 3 1800    # throttle

# Autonomous circle
mode LOITER
rc 3 1600

# Return home
mode RTL

# Follow waypoints
mode AUTO
```

---

## ArduCopter (Multirotor) Modes

### Manual Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `STABILIZE` | Self-level, manual throttle | Basic flying |
| `ALT_HOLD` | Altitude hold, manual position | Hovering |
| `LOITER` | GPS position hold | **Stable hovering** |
| `POSHOLD` | Like Loiter, smoother | Video work |

### Autonomous Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `GUIDED` | Accept external commands | **Best for RL** |
| `AUTO` | Follow waypoint mission | Autonomous flights |
| `RTL` | Return to launch and land | Emergency |
| `LAND` | Land at current position | End of flight |
| `BRAKE` | Stop and hold position | Emergency stop |

### Usage Examples

```bash
# Take off
mode GUIDED
arm throttle
takeoff 10

# Fly to position (lat, lon, alt)
guided -35.360 149.168 20

# Hover in place
mode LOITER

# Return and land
mode RTL

# Emergency land
mode LAND
```

---

## RC Channel Mapping

### Standard Channels

| Channel | Function | Range | Center |
|---------|----------|-------|--------|
| `rc 1` | Roll/Aileron | 1000-2000 | 1500 |
| `rc 2` | Pitch/Elevator | 1000-2000 | 1500 |
| `rc 3` | Throttle | 1000-2000 | varies |
| `rc 4` | Yaw/Rudder | 1000-2000 | 1500 |

### Control Examples

```bash
# Full throttle
rc 3 2000

# Half throttle
rc 3 1500

# Roll right
rc 1 1700

# Roll left
rc 1 1300

# Pitch up (climb for plane)
rc 2 1700

# Pitch down (descend for plane)
rc 2 1300

# Center all controls
rc 1 1500
rc 2 1500
rc 4 1500
```

---

## Mode Commands in MAVProxy

### Change Mode
```bash
mode GUIDED
mode FBWA
mode LOITER
mode RTL
```

### Arming
```bash
arm throttle        # Normal arm
arm throttle force  # Force arm (bypass checks)
disarm             # Disarm
```

### Takeoff (Copter)
```bash
takeoff 10         # Take off to 10 meters
```

### Navigation (Guided Mode)
```bash
# Copter: fly to GPS position at altitude
guided -35.360 149.168 20

# Set speed
setspeed 5
```

---

## Recommended Modes for RL Development

### For Quadcopter (ArduCopter)

**GUIDED mode** is best because:
- Accepts position/velocity commands
- Can hover (stationary target)
- Predictable dynamics
- Easy to send waypoints

```python
# Example RL action: send position command
mavproxy_command("guided -35.360 149.168 20")
```

### For Fixed-Wing (ArduPlane)

**GUIDED or FBWA** depending on needs:

**GUIDED** for waypoint following:
```bash
mode GUIDED
guided -35.360 149.168 100
```

**FBWA** for direct control:
```bash
mode FBWA
rc 3 1700  # throttle
rc 1 1600  # roll right
rc 2 1400  # pitch down
```

---

## Status Commands

```bash
# Overall status
status

# Attitude (roll, pitch, yaw)
attitude

# GPS position
position

# Current altitude
altitude

# All parameters
param show *

# Specific parameter
param show FRAME_CLASS
```

---

## Mode Switching Behavior

### Fixed-Wing Transitions
- Most modes require airspeed to maintain flight
- RTL will circle at home, not land (by default)
- LAND mode doesn't exist; use manual approach

### Copter Transitions
- Can switch between any modes mid-flight
- RTL will return home AND land
- LAND mode available for immediate landing

---

## Safety Notes

1. **Always have RTL as backup** - Set a switch or know the command
2. **Start with FBWA/LOITER** - These are stable and forgiving
3. **Test in simulation first** - SITL is your friend
4. **Know your failsafes** - Understand what happens on connection loss
